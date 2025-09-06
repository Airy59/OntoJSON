"""
Asynchronous tasks API endpoints.
"""

from flask import request, jsonify, current_app
from . import api_bp
from owl2jsonschema.services import TransformationService, FileService, ConfigurationService
from owl2jsonschema.services.file_service import WebUploadAdapter


# Task storage (in production, use Redis or database)
_tasks = {}


@api_bp.route('/tasks', methods=['POST'])
def create_task():
    """
    Create a new transformation task for async processing.
    
    Expects JSON body with:
    - sources: List of ontology sources
    - config: Optional transformation configuration
    - pipeline: Optional pipeline configuration
    """
    try:
        if not request.json or 'sources' not in request.json:
            return jsonify({'error': 'No sources provided'}), 400
        
        transformation_service = TransformationService()
        
        # Create task
        task_id = transformation_service.create_task(
            sources=request.json['sources'],
            config=request.json.get('config')
        )
        
        # Store additional parameters for async processing
        _tasks[task_id] = {
            'params': request.json,
            'status': 'pending'
        }
        
        # If Celery is enabled, queue the task
        if current_app.config.get('ENABLE_CELERY', False):
            from ..tasks import process_transformation
            process_transformation.delay(task_id, request.json)
        else:
            # For development, process synchronously
            _process_task_sync(task_id, request.json)
        
        return jsonify({
            'task_id': task_id,
            'status': 'pending',
            'message': 'Task created successfully'
        }), 202
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get the status of a transformation task."""
    try:
        transformation_service = TransformationService()
        task = transformation_service.get_task(task_id)
        
        if not task:
            return jsonify({'error': f'Task {task_id} not found'}), 404
        
        response = {
            'task_id': task.id,
            'status': task.status.value,
            'progress': task.progress,
            'message': task.message,
            'created_at': task.created_at,
            'completed_at': task.completed_at
        }
        
        if task.result:
            response['result'] = {
                'success': task.result.success,
                'schema': task.result.schema if task.result.success else None,
                'error': task.result.error,
                'warnings': task.result.warnings,
                'metadata': task.result.metadata
            }
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/tasks/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    """Cancel a running task."""
    try:
        transformation_service = TransformationService()
        task = transformation_service.get_task(task_id)
        
        if not task:
            return jsonify({'error': f'Task {task_id} not found'}), 404
        
        # Update task status
        from owl2jsonschema.services.transformation_service import TransformationStatus
        task.status = TransformationStatus.CANCELLED
        task.message = 'Task cancelled by user'
        
        # If using Celery, revoke the task
        if current_app.config.get('ENABLE_CELERY', False):
            from celery.task.control import revoke
            revoke(task_id, terminate=True)
        
        return jsonify({
            'task_id': task_id,
            'status': 'cancelled',
            'message': 'Task cancelled successfully'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """
    List all tasks for the current session.
    
    Query parameters:
    - status: Filter by status (pending, in_progress, completed, failed, cancelled)
    - limit: Maximum number of tasks to return (default: 20)
    - offset: Offset for pagination (default: 0)
    """
    try:
        transformation_service = TransformationService()
        
        # Get query parameters
        status_filter = request.args.get('status')
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        
        # Get all tasks (in production, filter by session/user)
        all_tasks = list(transformation_service.tasks.values())
        
        # Filter by status if specified
        if status_filter:
            from owl2jsonschema.services.transformation_service import TransformationStatus
            try:
                status = TransformationStatus(status_filter)
                all_tasks = [t for t in all_tasks if t.status == status]
            except ValueError:
                return jsonify({'error': f'Invalid status: {status_filter}'}), 400
        
        # Sort by creation time (newest first)
        all_tasks.sort(key=lambda t: t.created_at or '', reverse=True)
        
        # Apply pagination
        paginated_tasks = all_tasks[offset:offset + limit]
        
        # Format response
        tasks_data = []
        for task in paginated_tasks:
            task_info = {
                'task_id': task.id,
                'status': task.status.value,
                'progress': task.progress,
                'message': task.message,
                'created_at': task.created_at,
                'completed_at': task.completed_at,
                'sources': task.input_sources
            }
            tasks_data.append(task_info)
        
        return jsonify({
            'tasks': tasks_data,
            'total': len(all_tasks),
            'limit': limit,
            'offset': offset
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/tasks/<task_id>/result', methods=['GET'])
def get_task_result(task_id):
    """Get the result of a completed task."""
    try:
        transformation_service = TransformationService()
        task = transformation_service.get_task(task_id)
        
        if not task:
            return jsonify({'error': f'Task {task_id} not found'}), 404
        
        from owl2jsonschema.services.transformation_service import TransformationStatus
        if task.status != TransformationStatus.COMPLETED:
            return jsonify({
                'error': f'Task is not completed. Current status: {task.status.value}'
            }), 400
        
        if not task.result or not task.result.success:
            return jsonify({
                'error': task.result.error if task.result else 'No result available'
            }), 400
        
        return jsonify({
            'schema': task.result.schema,
            'metadata': task.result.metadata,
            'warnings': task.result.warnings
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _process_task_sync(task_id, params):
    """
    Process a task synchronously (for development without Celery).
    
    Args:
        task_id: Task ID
        params: Task parameters
    """
    try:
        # Initialize services
        file_service = FileService(WebUploadAdapter(current_app.config['UPLOAD_FOLDER']))
        transformation_service = TransformationService()
        config_service = ConfigurationService()
        
        # Update task status
        transformation_service.update_task_progress(task_id, 10, 'Starting transformation')
        
        # Process sources
        sources = params['sources']
        resolved_sources = []
        
        for source in sources:
            resolved_source, _ = file_service.resolve_source(source)
            resolved_sources.append(resolved_source)
        
        transformation_service.update_task_progress(task_id, 30, 'Sources resolved')
        
        # Get configuration
        config_dict = params.get('config')
        config = config_service.create_config_from_dict(config_dict)
        
        transformation_service.update_task_progress(task_id, 50, 'Performing transformation')
        
        # Perform transformation
        if len(resolved_sources) == 1:
            result = transformation_service.transform_single(
                source=resolved_sources[0],
                config=config
            )
        else:
            result = transformation_service.transform_multiple(
                sources=resolved_sources,
                config=config
            )
        
        transformation_service.update_task_progress(task_id, 90, 'Finalizing')
        
        # Complete task
        transformation_service.complete_task(task_id, result)
        
    except Exception as e:
        # Mark task as failed
        from owl2jsonschema.services.transformation_service import TransformationResult
        error_result = TransformationResult(
            success=False,
            error=str(e)
        )
        transformation_service.complete_task(task_id, error_result)


@api_bp.route('/tasks/cleanup', methods=['POST'])
def cleanup_tasks():
    """
    Clean up old completed tasks.
    
    Expects JSON body with:
    - older_than: ISO timestamp to delete tasks older than (optional)
    - status: Only delete tasks with this status (optional)
    """
    try:
        from datetime import datetime, timedelta
        transformation_service = TransformationService()
        
        # Get parameters
        older_than = request.json.get('older_than') if request.json else None
        status_filter = request.json.get('status') if request.json else None
        
        # Default to cleaning up tasks older than 24 hours
        if not older_than:
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            older_than = cutoff_time.isoformat()
        
        # Count tasks to be deleted
        deleted_count = 0
        tasks_to_delete = []
        
        for task_id, task in transformation_service.tasks.items():
            # Check age
            if task.completed_at and task.completed_at < older_than:
                # Check status filter if specified
                if status_filter:
                    from owl2jsonschema.services.transformation_service import TransformationStatus
                    if task.status.value == status_filter:
                        tasks_to_delete.append(task_id)
                else:
                    tasks_to_delete.append(task_id)
        
        # Delete tasks
        for task_id in tasks_to_delete:
            del transformation_service.tasks[task_id]
            if task_id in _tasks:
                del _tasks[task_id]
            deleted_count += 1
        
        return jsonify({
            'deleted': deleted_count,
            'message': f'Deleted {deleted_count} tasks'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
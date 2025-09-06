"""
Celery tasks for asynchronous processing.

This module provides async task processing for long-running transformations
using Celery with Redis as the message broker.
"""

from celery import Celery
from celery.utils.log import get_task_logger
from typing import Dict, Any, List
import os

# Initialize logger
logger = get_task_logger(__name__)

# Create Celery instance
celery_app = Celery(
    'owl2jsonschema_web',
    broker=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # Soft limit at 55 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)


@celery_app.task(bind=True, name='transform.process')
def process_transformation(self, task_id: str, params: Dict[str, Any]):
    """
    Process a transformation task asynchronously.
    
    Args:
        task_id: Unique task identifier
        params: Task parameters including sources and configuration
        
    Returns:
        Transformation result
    """
    from owl2jsonschema.services import (
        TransformationService,
        FileService,
        ConfigurationService
    )
    from owl2jsonschema.services.file_service import WebUploadAdapter
    
    try:
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'current': 10, 'total': 100, 'status': 'Initializing services...'}
        )
        
        # Initialize services
        upload_dir = os.environ.get('UPLOAD_FOLDER', '/tmp/ontojson_uploads')
        file_service = FileService(WebUploadAdapter(upload_dir))
        transformation_service = TransformationService()
        config_service = ConfigurationService()
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'current': 20, 'total': 100, 'status': 'Processing sources...'}
        )
        
        # Process sources
        sources = params.get('sources', [])
        resolved_sources = []
        
        for i, source in enumerate(sources):
            resolved_source, _ = file_service.resolve_source(source)
            resolved_sources.append(resolved_source)
            
            # Update progress for each source
            progress = 20 + (i + 1) * (30 / len(sources))
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': progress,
                    'total': 100,
                    'status': f'Resolved {i + 1} of {len(sources)} sources...'
                }
            )
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'current': 50, 'total': 100, 'status': 'Configuring transformation...'}
        )
        
        # Get configuration
        config_dict = params.get('config')
        config = config_service.create_config_from_dict(config_dict)
        
        # Update task in service
        transformation_service.update_task_progress(task_id, 60, 'Performing transformation...')
        
        # Check if we need to run the full pipeline
        pipeline_config = params.get('pipeline', {})
        
        if pipeline_config:
            # Run full pipeline
            self.update_state(
                state='PROGRESS',
                meta={'current': 70, 'total': 100, 'status': 'Running transformation pipeline...'}
            )
            
            tbox_result, abox_result, json_result = transformation_service.full_pipeline(
                sources=resolved_sources,
                config=config,
                generate_instances=pipeline_config.get('generate_instances', True),
                instance_count=pipeline_config.get('instance_count', 10),
                output_format=pipeline_config.get('output_format', 'json')
            )
            
            # Prepare comprehensive result
            result = {
                'success': tbox_result.success,
                'schema': tbox_result.schema if tbox_result.success else None,
                'error': tbox_result.error,
                'metadata': tbox_result.metadata
            }
            
            if abox_result:
                result['abox'] = {
                    'success': abox_result.success,
                    'data': abox_result.schema if abox_result.success else None
                }
            
            if json_result:
                result['instances'] = json_result.schema if json_result.success else None
            
        else:
            # Simple transformation
            self.update_state(
                state='PROGRESS',
                meta={'current': 70, 'total': 100, 'status': 'Transforming ontology...'}
            )
            
            if len(resolved_sources) == 1:
                transform_result = transformation_service.transform_single(
                    source=resolved_sources[0],
                    config=config,
                    language=params.get('language', 'en')
                )
            else:
                transform_result = transformation_service.transform_multiple(
                    sources=resolved_sources,
                    composite_metadata=params.get('composite_metadata'),
                    config=config,
                    language=params.get('language', 'en')
                )
            
            result = {
                'success': transform_result.success,
                'schema': transform_result.schema if transform_result.success else None,
                'error': transform_result.error,
                'metadata': transform_result.metadata,
                'warnings': transform_result.warnings
            }
        
        # Update final progress
        self.update_state(
            state='PROGRESS',
            meta={'current': 90, 'total': 100, 'status': 'Finalizing results...'}
        )
        
        # Complete task in service
        transformation_service.complete_task(task_id, transform_result if not pipeline_config else tbox_result)
        
        # Return success
        return {
            'task_id': task_id,
            'status': 'completed',
            'result': result
        }
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {str(e)}")
        
        # Mark task as failed
        from owl2jsonschema.services.transformation_service import TransformationResult
        error_result = TransformationResult(
            success=False,
            error=str(e)
        )
        
        # Try to update task status
        try:
            transformation_service.complete_task(task_id, error_result)
        except:
            pass
        
        # Raise to Celery for proper error handling
        raise


@celery_app.task(bind=True, name='transform.validate')
def validate_ontology_async(self, source: str):
    """
    Validate an ontology source asynchronously.
    
    Args:
        source: Ontology source (URL or file path)
        
    Returns:
        Validation result
    """
    from owl2jsonschema.services import TransformationService, FileService
    from owl2jsonschema.services.file_service import WebUploadAdapter
    
    try:
        # Update state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Validating ontology...'}
        )
        
        # Initialize services
        upload_dir = os.environ.get('UPLOAD_FOLDER', '/tmp/ontojson_uploads')
        file_service = FileService(WebUploadAdapter(upload_dir))
        transformation_service = TransformationService()
        
        # Resolve source
        resolved_source, _ = file_service.resolve_source(source)
        
        # Validate
        is_valid, error = transformation_service.validate_ontology_source(resolved_source)
        
        return {
            'valid': is_valid,
            'error': error,
            'source': source
        }
        
    except Exception as e:
        logger.error(f"Validation failed for {source}: {str(e)}")
        return {
            'valid': False,
            'error': str(e),
            'source': source
        }


@celery_app.task(name='transform.cleanup')
def cleanup_old_tasks():
    """
    Periodic task to clean up old completed tasks.
    
    This should be scheduled to run periodically (e.g., daily).
    """
    from datetime import datetime, timedelta
    from owl2jsonschema.services import TransformationService
    
    try:
        logger.info("Starting cleanup of old tasks...")
        
        transformation_service = TransformationService()
        
        # Delete tasks older than 7 days
        cutoff_time = datetime.utcnow() - timedelta(days=7)
        cutoff_iso = cutoff_time.isoformat()
        
        deleted_count = 0
        tasks_to_delete = []
        
        for task_id, task in transformation_service.tasks.items():
            if task.completed_at and task.completed_at < cutoff_iso:
                tasks_to_delete.append(task_id)
        
        for task_id in tasks_to_delete:
            del transformation_service.tasks[task_id]
            deleted_count += 1
        
        logger.info(f"Cleanup completed. Deleted {deleted_count} old tasks.")
        
        return {
            'deleted': deleted_count,
            'cutoff': cutoff_iso
        }
        
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        raise


# Celery beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'cleanup-old-tasks': {
        'task': 'transform.cleanup',
        'schedule': 86400.0,  # Run daily (86400 seconds = 24 hours)
        'options': {
            'expires': 3600.0,  # Expire if not run within 1 hour
        }
    },
}


# Worker configuration
@celery_app.task
def debug_task():
    """Debug task to test Celery connection."""
    return {
        'status': 'Celery is working!',
        'broker': celery_app.conf.broker_url,
        'backend': celery_app.conf.result_backend
    }


# Initialize Celery when module is imported
def init_celery(app=None):
    """
    Initialize Celery with Flask app context.
    
    Args:
        app: Flask application instance
    """
    if app:
        # Update configuration from Flask app
        celery_app.conf.update(app.config)
        
        # Set up Flask app context for tasks
        class ContextTask(celery_app.Task):
            """Make celery tasks work with Flask app context."""
            
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)
        
        celery_app.Task = ContextTask
    
    return celery_app
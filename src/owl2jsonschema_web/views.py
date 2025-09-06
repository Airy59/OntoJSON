"""
Web UI views for the Flask application.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename
import json
import os

# Create main blueprint for web UI
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Main landing page."""
    return render_template('index.html')


@main_bp.route('/transform')
def transform():
    """Transformation page."""
    return render_template('transform.html')


@main_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    """File upload page."""
    if request.method == 'POST':
        from flask import current_app
        from owl2jsonschema.services import FileService
        from owl2jsonschema.services.file_service import WebUploadAdapter
        
        file_service = FileService(WebUploadAdapter(current_app.config['UPLOAD_FOLDER']))
        
        uploaded_files = []
        
        # Handle multiple file uploads
        for key in request.files:
            file = request.files[key]
            if file and file.filename:
                filename = secure_filename(file.filename)
                # Save file using the web upload adapter
                upload_adapter = file_service.adapter
                if isinstance(upload_adapter, WebUploadAdapter):
                    file_path = upload_adapter.save_upload(file, filename)
                    uploaded_files.append({
                        'name': filename,
                        'path': file_path
                    })
        
        # Store uploaded files in session
        if 'uploaded_files' not in session:
            session['uploaded_files'] = []
        session['uploaded_files'].extend(uploaded_files)
        session.modified = True
        
        flash(f'Successfully uploaded {len(uploaded_files)} file(s)', 'success')
        return jsonify({
            'success': True,
            'files': uploaded_files
        })
    
    return render_template('upload.html')


@main_bp.route('/configure')
def configure():
    """Configuration management page."""
    return render_template('configure.html')


@main_bp.route('/results/<task_id>')
def results(task_id):
    """Results page for a specific transformation task."""
    return render_template('results.html', task_id=task_id)


@main_bp.route('/documentation')
def documentation():
    """Documentation page."""
    return render_template('documentation.html')


@main_bp.route('/api-docs')
def api_docs():
    """API documentation page."""
    return render_template('api_docs.html')


@main_bp.route('/about')
def about():
    """About page."""
    return render_template('about.html')


@main_bp.route('/session/clear', methods=['POST'])
def clear_session():
    """Clear session data."""
    session.clear()
    flash('Session cleared', 'info')
    return redirect(url_for('main.index'))


@main_bp.route('/session/files')
def get_session_files():
    """Get list of files in current session."""
    files = session.get('uploaded_files', [])
    return jsonify({
        'files': files,
        'count': len(files)
    })


@main_bp.route('/session/files/<file_path>', methods=['DELETE'])
def remove_session_file(file_path):
    """Remove a file from session."""
    if 'uploaded_files' in session:
        session['uploaded_files'] = [
            f for f in session['uploaded_files']
            if f.get('path') != file_path
        ]
        session.modified = True
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'File not found'}), 404
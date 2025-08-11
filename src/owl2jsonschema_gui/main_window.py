"""
Main window for the OWL to JSON Schema GUI application with T-box/A-box workflow.
"""

import sys
import json
import traceback
from pathlib import Path
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTextEdit,
    QGroupBox, QCheckBox, QScrollArea, QMessageBox,
    QTabWidget, QComboBox, QSpinBox, QLineEdit,
    QSplitter, QProgressBar, QStatusBar, QFrame, QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QAction, QIcon

# Import the transformation engine and A-box generator
from owl2jsonschema import TransformationEngine, TransformationConfig, OntologyParser, ABoxGenerator
from owl2jsonschema.reasoner import ABoxValidator


class TransformationWorker(QThread):
    """Worker thread for running the transformation without blocking the GUI."""
    
    progress = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal(dict)
    
    def __init__(self, input_source: str, config: Dict[str, Any]):
        super().__init__()
        self.input_source = input_source.strip()
        self.config = config
    
    def run(self):
        """Run the transformation in a separate thread."""
        try:
            # Check if input is a URL
            is_url = self.input_source.startswith(('http://', 'https://', 'ftp://'))
            
            if is_url:
                self.progress.emit(f"Loading ontology from URL: {self.input_source}")
                
                # Try using requests library first (better SSL handling)
                try:
                    import requests
                    import tempfile
                    
                    headers = {
                        'Accept': 'application/rdf+xml, text/turtle, application/ld+json, application/n-triples, text/n3;q=0.9, application/xml;q=0.8, */*;q=0.5'
                    }
                    response = requests.get(self.input_source, headers=headers, verify=True, timeout=30)
                    response.raise_for_status()
                    
                    content_type = response.headers.get('Content-Type', '').lower()
                    self.progress.emit(f"Content-Type: {content_type}")
                    
                    # Determine format and save to temp file
                    rdf_format = None
                    suffix = '.rdf'
                    
                    if 'turtle' in content_type:
                        rdf_format = 'turtle'
                        suffix = '.ttl'
                    elif 'json-ld' in content_type:
                        rdf_format = 'json-ld'
                        suffix = '.jsonld'
                    
                    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
                        tmp_file.write(response.content)
                        tmp_path = tmp_file.name
                    
                    self.progress.emit(f"Parsing ontology (format: {rdf_format or 'auto-detect'})...")
                    parser = OntologyParser()
                    ontology = parser.parse(tmp_path, format=rdf_format)
                    
                    # Clean up temp file
                    import os
                    os.unlink(tmp_path)
                    
                except ImportError:
                    # Fallback to direct parsing
                    self.progress.emit("Attempting direct parsing...")
                    parser = OntologyParser()
                    ontology = parser.parse(self.input_source)
            else:
                self.progress.emit(f"Parsing ontology from file: {self.input_source}")
                parser = OntologyParser()
                ontology = parser.parse(self.input_source)
            
            self.progress.emit(f"Parsed {len(ontology.classes)} classes, "
                             f"{len(ontology.object_properties)} object properties, "
                             f"{len(ontology.datatype_properties)} datatype properties")
            
            # Store ontology model for A-box generation
            self.ontology_model = ontology
            
            self.progress.emit("Running transformation...")
            config = TransformationConfig(self.config)
            engine = TransformationEngine(config)
            result = engine.transform(ontology)
            
            self.progress.emit("Transformation completed!")
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(f"Error during transformation: {str(e)}\n{traceback.format_exc()}")


class MainWindow(QMainWindow):
    """Main window of the OWL to JSON Schema GUI application with T-box/A-box workflow."""
    
    def __init__(self):
        super().__init__()
        self.input_file: Optional[str] = None
        self.transformation_result: Optional[Dict] = None
        self.ontology_model = None
        self.abox_data = None
        self.json_instances = None
        
        # Workflow state
        self.tbox_ready = False
        self.abox_ready = False
        self.json_ready = False
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("OWL to JSON Schema Transformer - T-box/A-box Workflow")
        self.setGeometry(100, 100, 1400, 900)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        central_widget.setLayout(main_layout)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create workflow tabs
        self.create_workflow_area(main_layout)
        
        # Create status bar
        self.create_status_bar()
        
        # Apply styles
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                opacity: 0.8;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
    
    def create_menu_bar(self):
        """Create the menu bar."""
        menubar = self.menuBar()
        menubar.setNativeMenuBar(False)
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        open_action = QAction("&Open OWL File...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.browse_input_file)
        file_menu.addAction(open_action)
        
        open_url_action = QAction("Open from &URL...", self)
        open_url_action.setShortcut("Ctrl+U")
        open_url_action.triggered.connect(self.open_url)
        file_menu.addAction(open_url_action)
        
        file_menu.addSeparator()
        
        save_schema_action = QAction("Save JSON &Schema...", self)
        save_schema_action.setShortcut("Ctrl+S")
        save_schema_action.triggered.connect(self.save_schema)
        file_menu.addAction(save_schema_action)
        
        save_abox_action = QAction("Save &A-box...", self)
        save_abox_action.triggered.connect(self.save_abox)
        save_abox_action.setEnabled(False)
        self.save_abox_action = save_abox_action
        file_menu.addAction(save_abox_action)
        
        save_json_action = QAction("Save &JSON Instance...", self)
        save_json_action.triggered.connect(self.save_json)
        save_json_action.setEnabled(False)
        self.save_json_action = save_json_action
        file_menu.addAction(save_json_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        
        validate_action = QAction("&Validate A-box with Reasoner", self)
        validate_action.setEnabled(False)
        self.validate_action = validate_action
        tools_menu.addAction(validate_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_workflow_area(self, parent_layout):
        """Create the three-step workflow area."""
        self.workflow_tabs = QTabWidget()
        self.workflow_tabs.setTabPosition(QTabWidget.TabPosition.North)
        
        # Step 1: T-box Transformation
        self.tbox_widget = self.create_tbox_step()
        self.workflow_tabs.addTab(self.tbox_widget, "1. T-box Transformation")
        
        # Step 2: A-box Generation
        self.abox_widget = self.create_abox_step()
        self.workflow_tabs.addTab(self.abox_widget, "2. A-box Generation")
        self.workflow_tabs.setTabEnabled(1, False)
        
        # Step 3: JSON Instance Generation
        self.json_widget = self.create_json_step()
        self.workflow_tabs.addTab(self.json_widget, "3. JSON Instance Generation")
        self.workflow_tabs.setTabEnabled(2, False)
        
        parent_layout.addWidget(self.workflow_tabs)
    
    def create_tbox_step(self):
        """Create the T-box transformation step widget."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Description
        desc_label = QLabel("<b>Step 1: T-box Transformation</b><br>"
                          "Transform OWL ontology (T-box) to JSON Schema")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("QLabel { background-color: #e3f2fd; padding: 10px; border-radius: 5px; }")
        layout.addWidget(desc_label)
        
        # Input section
        input_group = QGroupBox("Input")
        input_layout = QHBoxLayout()
        
        self.file_label = QLabel("No file selected")
        self.file_label.setMaximumWidth(400)
        input_layout.addWidget(self.file_label)
        
        open_btn = QPushButton("Open OWL File")
        open_btn.clicked.connect(self.browse_input_file)
        input_layout.addWidget(open_btn)
        
        url_btn = QPushButton("Open from URL")
        url_btn.clicked.connect(self.open_url)
        input_layout.addWidget(url_btn)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # Configuration section
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout()
        
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Language:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["en", "fr", "de", "es"])
        lang_layout.addWidget(self.lang_combo)
        lang_layout.addStretch()
        config_layout.addLayout(lang_layout)
        
        self.include_uri_check = QCheckBox("Include URI in comments")
        config_layout.addWidget(self.include_uri_check)
        
        self.use_arrays_check = QCheckBox("Use arrays for multi-valued properties")
        self.use_arrays_check.setChecked(True)
        config_layout.addWidget(self.use_arrays_check)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Transform button
        self.transform_btn = QPushButton("Transform T-box to JSON Schema")
        self.transform_btn.clicked.connect(self.run_transformation)
        self.transform_btn.setEnabled(False)
        self.transform_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        layout.addWidget(self.transform_btn)
        
        # Output section
        output_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # OWL Input display
        owl_group = QGroupBox("OWL Ontology")
        owl_layout = QVBoxLayout()
        self.input_text = QTextEdit()
        self.input_text.setFont(QFont("Courier", 10))
        owl_layout.addWidget(self.input_text)
        owl_group.setLayout(owl_layout)
        output_splitter.addWidget(owl_group)
        
        # JSON Schema output with tabs
        schema_group = QGroupBox("JSON Schema Output")
        schema_layout = QVBoxLayout()
        
        # Create tab widget for schema and statistics
        self.schema_tabs = QTabWidget()
        
        # Schema tab
        self.output_text = QTextEdit()
        self.output_text.setFont(QFont("Courier", 10))
        self.output_text.setReadOnly(True)
        self.schema_tabs.addTab(self.output_text, "Schema")
        
        # Statistics tab
        self.stats_text = QTextEdit()
        self.stats_text.setFont(QFont("Courier", 10))
        self.stats_text.setReadOnly(True)
        self.schema_tabs.addTab(self.stats_text, "Statistics")
        
        schema_layout.addWidget(self.schema_tabs)
        schema_group.setLayout(schema_layout)
        output_splitter.addWidget(schema_group)
        
        output_splitter.setSizes([600, 600])
        layout.addWidget(output_splitter)
        
        widget.setLayout(layout)
        return widget
    
    def create_abox_step(self):
        """Create the A-box generation step widget."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Description
        desc_label = QLabel("<b>Step 2: A-box Generation</b><br>"
                          "Generate random individuals and property instances that comply with the T-box")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("QLabel { background-color: #fff3e0; padding: 10px; border-radius: 5px; }")
        layout.addWidget(desc_label)
        
        # Configuration
        config_group = QGroupBox("Generation Configuration")
        config_layout = QVBoxLayout()
        
        uri_layout = QHBoxLayout()
        uri_layout.addWidget(QLabel("Base URI:"))
        self.base_uri_input = QLineEdit("https://example.org#")
        self.base_uri_input.setEnabled(False)
        uri_layout.addWidget(self.base_uri_input)
        config_layout.addLayout(uri_layout)
        
        min_layout = QHBoxLayout()
        min_layout.addWidget(QLabel("Min instances per class:"))
        self.min_instances_spin = QSpinBox()
        self.min_instances_spin.setMinimum(1)
        self.min_instances_spin.setMaximum(10)
        self.min_instances_spin.setValue(1)
        self.min_instances_spin.setEnabled(False)
        min_layout.addWidget(self.min_instances_spin)
        min_layout.addStretch()
        config_layout.addLayout(min_layout)
        
        max_layout = QHBoxLayout()
        max_layout.addWidget(QLabel("Max instances per class:"))
        self.max_instances_spin = QSpinBox()
        self.max_instances_spin.setMinimum(1)
        self.max_instances_spin.setMaximum(20)
        self.max_instances_spin.setValue(3)
        self.max_instances_spin.setEnabled(False)
        max_layout.addWidget(self.max_instances_spin)
        max_layout.addStretch()
        config_layout.addLayout(max_layout)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Generate button
        self.generate_abox_btn = QPushButton("Generate A-box")
        self.generate_abox_btn.setEnabled(False)
        self.generate_abox_btn.clicked.connect(self.generate_abox)
        self.generate_abox_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        layout.addWidget(self.generate_abox_btn)
        
        # Validation section
        validation_group = QGroupBox("Validation")
        validation_layout = QHBoxLayout()
        
        self.validate_btn = QPushButton("Validate with Reasoner")
        self.validate_btn.setEnabled(False)
        self.validate_btn.clicked.connect(self.validate_abox)
        validation_layout.addWidget(self.validate_btn)
        
        self.validation_status = QLabel("Not validated")
        self.validation_status.setStyleSheet("color: gray;")
        validation_layout.addWidget(self.validation_status)
        
        validation_layout.addStretch()
        validation_group.setLayout(validation_layout)
        layout.addWidget(validation_group)
        
        # Output
        abox_output_group = QGroupBox("Generated A-box (RDF/OWL)")
        abox_output_layout = QVBoxLayout()
        self.abox_output_text = QTextEdit()
        self.abox_output_text.setFont(QFont("Courier", 10))
        self.abox_output_text.setReadOnly(True)
        abox_output_layout.addWidget(self.abox_output_text)
        abox_output_group.setLayout(abox_output_layout)
        layout.addWidget(abox_output_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_json_step(self):
        """Create the JSON instance generation step widget."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Description
        desc_label = QLabel("<b>Step 3: JSON Instance Generation</b><br>"
                          "Transform the A-box to JSON instances conforming to the generated JSON Schema")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("QLabel { background-color: #e8f5e9; padding: 10px; border-radius: 5px; }")
        layout.addWidget(desc_label)
        
        # Transform button
        self.transform_json_btn = QPushButton("Transform A-box to JSON")
        self.transform_json_btn.setEnabled(False)
        self.transform_json_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        layout.addWidget(self.transform_json_btn)
        
        # Validation
        validation_group = QGroupBox("Schema Validation")
        validation_layout = QHBoxLayout()
        
        self.validate_json_btn = QPushButton("Validate against Schema")
        self.validate_json_btn.setEnabled(False)
        validation_layout.addWidget(self.validate_json_btn)
        
        self.json_validation_status = QLabel("Not validated")
        self.json_validation_status.setStyleSheet("color: gray;")
        validation_layout.addWidget(self.json_validation_status)
        
        validation_layout.addStretch()
        validation_group.setLayout(validation_layout)
        layout.addWidget(validation_group)
        
        # Output
        json_output_group = QGroupBox("JSON Instance Output")
        json_output_layout = QVBoxLayout()
        self.json_output_text = QTextEdit()
        self.json_output_text.setFont(QFont("Courier", 10))
        self.json_output_text.setReadOnly(True)
        json_output_layout.addWidget(self.json_output_text)
        json_output_group.setLayout(json_output_layout)
        layout.addWidget(json_output_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_status_bar(self):
        """Create the status bar with workflow indicators."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addWidget(self.progress_bar)
        
        # Status message
        self.status_message = QLabel("Ready")
        self.status_bar.addWidget(self.status_message)
        
        # Add permanent status widgets
        self.tbox_status = QLabel("T-box: Not Ready")
        self.tbox_status.setStyleSheet("QLabel { color: red; font-weight: bold; }")
        self.status_bar.addPermanentWidget(self.tbox_status)
        
        separator1 = QFrame()
        separator1.setFrameStyle(QFrame.Shape.VLine)
        self.status_bar.addPermanentWidget(separator1)
        
        self.abox_status = QLabel("A-box: Not Generated")
        self.abox_status.setStyleSheet("QLabel { color: gray; }")
        self.status_bar.addPermanentWidget(self.abox_status)
        
        separator2 = QFrame()
        separator2.setFrameStyle(QFrame.Shape.VLine)
        self.status_bar.addPermanentWidget(separator2)
        
        self.json_status = QLabel("JSON: Not Available")
        self.json_status.setStyleSheet("QLabel { color: gray; }")
        self.status_bar.addPermanentWidget(self.json_status)
    
    def update_status(self):
        """Update the status bar indicators."""
        # T-box status
        if self.tbox_ready:
            self.tbox_status.setText("T-box: Ready ✓")
            self.tbox_status.setStyleSheet("QLabel { color: green; font-weight: bold; }")
            self.workflow_tabs.setTabEnabled(1, True)
            self.enable_abox_controls(True)
        else:
            self.tbox_status.setText("T-box: Not Ready")
            self.tbox_status.setStyleSheet("QLabel { color: red; font-weight: bold; }")
            self.workflow_tabs.setTabEnabled(1, False)
            self.workflow_tabs.setTabEnabled(2, False)
        
        # A-box status
        if self.abox_ready:
            self.abox_status.setText("A-box: Generated ✓")
            self.abox_status.setStyleSheet("QLabel { color: green; font-weight: bold; }")
            self.workflow_tabs.setTabEnabled(2, True)
            self.save_abox_action.setEnabled(True)
            self.validate_action.setEnabled(True)
            self.transform_json_btn.setEnabled(True)
        else:
            self.abox_status.setText("A-box: Not Generated")
            self.abox_status.setStyleSheet("QLabel { color: gray; }")
            self.workflow_tabs.setTabEnabled(2, False)
            self.save_abox_action.setEnabled(False)
            self.validate_action.setEnabled(False)
        
        # JSON status
        if self.json_ready:
            self.json_status.setText("JSON: Available ✓")
            self.json_status.setStyleSheet("QLabel { color: green; font-weight: bold; }")
            self.save_json_action.setEnabled(True)
            self.validate_json_btn.setEnabled(True)
        else:
            self.json_status.setText("JSON: Not Available")
            self.json_status.setStyleSheet("QLabel { color: gray; }")
            self.save_json_action.setEnabled(False)
    
    def enable_abox_controls(self, enabled: bool):
        """Enable or disable A-box generation controls."""
        self.base_uri_input.setEnabled(enabled)
        self.min_instances_spin.setEnabled(enabled)
        self.max_instances_spin.setEnabled(enabled)
        self.generate_abox_btn.setEnabled(enabled)
        
        style = "" if enabled else "QWidget { color: gray; }"
        self.base_uri_input.setStyleSheet(style)
        self.min_instances_spin.setStyleSheet(style)
        self.max_instances_spin.setStyleSheet(style)
    
    def browse_input_file(self):
        """Browse for input ontology file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Ontology File",
            "",
            "Ontology Files (*.owl *.rdf *.xml *.ttl *.n3);;All Files (*.*)"
        )
        
        if file_path:
            self.input_file = file_path
            self.file_label.setText(Path(file_path).name)
            self.transform_btn.setEnabled(True)
            
            # Load and display file content
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    self.input_text.setPlainText(content[:5000])  # Show first 5000 chars
            except Exception as e:
                self.input_text.setPlainText(f"Error loading file: {str(e)}")
    
    def open_url(self):
        """Open ontology from URL."""
        from PyQt6.QtWidgets import QInputDialog
        
        url, ok = QInputDialog.getText(
            self,
            "Open from URL",
            "Enter the URL of the OWL/RDF ontology:",
            text="https://"
        )
        
        if ok and url:
            self.input_file = url
            self.file_label.setText(url)
            self.transform_btn.setEnabled(True)
            self.input_text.setPlainText(f"URL: {url}\n\n(Content will be loaded during transformation)")
    
    def run_transformation(self):
        """Run the T-box transformation."""
        if not self.input_file:
            QMessageBox.warning(self, "Warning", "Please select an input file first.")
            return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.transform_btn.setEnabled(False)
        
        # Get configuration
        config = {
            "rules": {
                "class_to_object": {"enabled": True},
                "class_hierarchy": {"enabled": True},
                "class_restrictions": {"enabled": True},
                "object_property": {"enabled": True},
                "datatype_property": {"enabled": True},
                "property_cardinality": {"enabled": True},
                "labels_to_titles": {"enabled": True, "options": {"language": self.lang_combo.currentText()}},
                "enumeration_to_enum": {"enabled": True},
                "ontology_metadata": {"enabled": True}
            },
            "output": {
                "include_uri": self.include_uri_check.isChecked(),
                "use_arrays": self.use_arrays_check.isChecked()
            }
        }
        
        # Create and start worker thread
        self.worker = TransformationWorker(self.input_file, config)
        self.worker.progress.connect(self.on_progress)
        self.worker.error.connect(self.on_error)
        self.worker.finished.connect(self.on_transformation_complete)
        self.worker.start()
    
    def on_progress(self, message: str):
        """Handle progress updates."""
        self.status_message.setText(message)
    
    def on_error(self, error_message: str):
        """Handle transformation errors."""
        self.progress_bar.setVisible(False)
        self.transform_btn.setEnabled(True)
        QMessageBox.critical(self, "Transformation Error", error_message)
    
    def on_transformation_complete(self, result: Dict):
        """Handle transformation completion."""
        self.transformation_result = result
        
        # Store the ontology model for A-box generation
        if hasattr(self.worker, 'ontology_model'):
            self.ontology_model = self.worker.ontology_model
        
        # Display result
        output_text = json.dumps(result, indent=2)
        self.output_text.setPlainText(output_text)
        
        # Generate and display statistics
        stats = self.generate_statistics(result)
        self.stats_text.setPlainText(stats)
        
        # Update state
        self.tbox_ready = True
        self.update_status()
        
        # Update UI
        self.progress_bar.setVisible(False)
        self.transform_btn.setEnabled(True)
        self.status_message.setText("T-box transformation completed!")
    
    def generate_statistics(self, schema: Dict) -> str:
        """Generate transformation statistics from the schema."""
        stats = []
        stats.append("=" * 50)
        stats.append("TRANSFORMATION STATISTICS")
        stats.append("=" * 50)
        stats.append("")
        
        # Count definitions
        definitions = schema.get('definitions', {})
        num_definitions = len(definitions)
        stats.append(f"Total Definitions: {num_definitions}")
        stats.append("")
        
        # Analyze each definition
        class_count = 0
        property_counts = {}
        required_counts = {}
        total_properties = 0
        
        for def_name, def_schema in definitions.items():
            if def_schema.get('type') == 'object':
                class_count += 1
                
                # Count properties
                properties = def_schema.get('properties', {})
                prop_count = len(properties)
                property_counts[def_name] = prop_count
                total_properties += prop_count
                
                # Count required properties
                required = def_schema.get('required', [])
                required_counts[def_name] = len(required)
        
        stats.append(f"Object Types: {class_count}")
        stats.append(f"Total Properties: {total_properties}")
        if class_count > 0:
            avg_properties = total_properties / class_count
            stats.append(f"Average Properties per Object: {avg_properties:.1f}")
        stats.append("")
        
        # Detailed breakdown
        stats.append("-" * 50)
        stats.append("DETAILED BREAKDOWN")
        stats.append("-" * 50)
        stats.append("")
        
        for def_name in sorted(definitions.keys()):
            def_schema = definitions[def_name]
            stats.append(f"• {def_name}")
            
            # Type
            if 'type' in def_schema:
                stats.append(f"  Type: {def_schema['type']}")
            
            # Properties count
            if def_name in property_counts:
                stats.append(f"  Properties: {property_counts[def_name]}")
                
                # List property names
                properties = def_schema.get('properties', {})
                if properties:
                    prop_names = sorted(properties.keys())
                    for prop_name in prop_names:
                        prop_schema = properties[prop_name]
                        prop_type = prop_schema.get('type', 'unknown')
                        if '$ref' in prop_schema:
                            prop_type = f"ref to {prop_schema['$ref'].split('/')[-1]}"
                        elif 'items' in prop_schema and '$ref' in prop_schema['items']:
                            prop_type = f"array of {prop_schema['items']['$ref'].split('/')[-1]}"
                        stats.append(f"    - {prop_name}: {prop_type}")
            
            # Required properties
            if def_name in required_counts and required_counts[def_name] > 0:
                stats.append(f"  Required Properties: {required_counts[def_name]}")
                required = def_schema.get('required', [])
                if required:
                    stats.append(f"    {', '.join(required)}")
            
            # Enum values
            if 'enum' in def_schema:
                stats.append(f"  Enum Values: {len(def_schema['enum'])}")
                stats.append(f"    {', '.join(str(v) for v in def_schema['enum'][:10])}")
                if len(def_schema['enum']) > 10:
                    stats.append(f"    ... and {len(def_schema['enum']) - 10} more")
            
            # AllOf references
            if 'allOf' in def_schema:
                refs = [item.get('$ref', '').split('/')[-1] for item in def_schema['allOf'] if '$ref' in item]
                if refs:
                    stats.append(f"  Inherits from: {', '.join(refs)}")
            
            stats.append("")
        
        # Summary
        stats.append("-" * 50)
        stats.append("SUMMARY")
        stats.append("-" * 50)
        
        # Calculate complexity metrics
        simple_types = sum(1 for d in definitions.values() if d.get('type') not in ['object', 'array'])
        complex_types = num_definitions - simple_types
        
        stats.append(f"Simple Types: {simple_types}")
        stats.append(f"Complex Types: {complex_types}")
        
        # Count inheritance relationships
        inheritance_count = sum(1 for d in definitions.values() if 'allOf' in d)
        if inheritance_count > 0:
            stats.append(f"Inheritance Relationships: {inheritance_count}")
        
        # Count enumerations
        enum_count = sum(1 for d in definitions.values() if 'enum' in d)
        if enum_count > 0:
            stats.append(f"Enumerations: {enum_count}")
        
        return "\n".join(stats)
    
    def save_schema(self):
        """Save the JSON Schema."""
        if not self.transformation_result:
            QMessageBox.warning(self, "Warning", "No schema to save. Please run the transformation first.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save JSON Schema",
            "schema.json",
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(self.transformation_result, f, indent=2)
                QMessageBox.information(self, "Success", f"Schema saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save file:\n{str(e)}")
    
    def generate_abox(self):
        """Generate the A-box based on the T-box."""
        if not self.ontology_model:
            QMessageBox.warning(self, "Warning", "Please transform the T-box first.")
            return
        
        try:
            # Get configuration
            base_uri = self.base_uri_input.text().strip()
            if not base_uri:
                base_uri = "https://example.org#"
            
            min_instances = self.min_instances_spin.value()
            max_instances = self.max_instances_spin.value()
            
            # Ensure min <= max
            if min_instances > max_instances:
                QMessageBox.warning(self, "Warning", "Minimum instances cannot be greater than maximum instances.")
                return
            
            # Update status
            self.status_message.setText("Generating A-box...")
            self.generate_abox_btn.setEnabled(False)
            
            # Generate A-box
            generator = ABoxGenerator(self.ontology_model, base_uri)
            abox_graph = generator.generate(min_instances, max_instances)
            
            # Serialize to Turtle format
            abox_content = generator.serialize(format='turtle')
            
            # Display in output
            self.abox_output_text.setPlainText(abox_content)
            
            # Store for later use
            self.abox_data = abox_graph
            
            # Update state
            self.abox_ready = True
            self.update_status()
            
            # Update UI
            self.generate_abox_btn.setEnabled(True)
            self.validate_btn.setEnabled(True)
            self.validation_status.setText("Not validated")
            self.validation_status.setStyleSheet("color: gray;")
            self.status_message.setText("A-box generated successfully!")
            
            QMessageBox.information(self, "Success",
                                  f"A-box generated with {len(list(abox_graph.subjects(predicate=None, object=None)))} individuals.")
            
        except Exception as e:
            self.generate_abox_btn.setEnabled(True)
            QMessageBox.critical(self, "Generation Error", f"Failed to generate A-box:\n{str(e)}")
    
    def save_abox(self):
        """Save the generated A-box."""
        if not self.abox_data:
            QMessageBox.warning(self, "Warning", "No A-box to save. Please generate the A-box first.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save A-box",
            "abox.ttl",
            "Turtle Files (*.ttl);;RDF/XML Files (*.rdf *.xml);;N-Triples Files (*.nt);;All Files (*.*)"
        )
        
        if file_path:
            try:
                # Determine format from file extension
                if file_path.endswith('.ttl'):
                    format = 'turtle'
                elif file_path.endswith('.rdf') or file_path.endswith('.xml'):
                    format = 'xml'
                elif file_path.endswith('.nt'):
                    format = 'nt'
                else:
                    format = 'turtle'  # Default
                
                # Serialize and save
                content = self.abox_data.serialize(format=format)
                with open(file_path, 'w') as f:
                    f.write(content)
                
                QMessageBox.information(self, "Success", f"A-box saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save file:\n{str(e)}")
    
    def save_json(self):
        """Save the JSON instances."""
        QMessageBox.information(self, "Not Implemented", 
                               "JSON instance generation functionality will be implemented in the next phase.")
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About OWL to JSON Schema Converter",
            "OWL to JSON Schema Converter\n"
            "Version 1.0\n\n"
            "A tool for transforming OWL ontologies to JSON Schema\n"
            "with T-box/A-box workflow support.\n\n"
            "© 2024 All rights reserved."
        )
    
    def validate_abox(self):
        """Validate the A-box against the T-box using OWL-RL reasoner."""
        if not self.abox_data:
            QMessageBox.warning(self, "Warning", "No A-box to validate. Please generate an A-box first.")
            return
        
        if not self.input_file:
            QMessageBox.warning(self, "Warning", "No T-box loaded. Please load an ontology first.")
            return
        
        try:
            # Update status
            self.validation_status.setText("Validating...")
            self.validation_status.setStyleSheet("color: blue;")
            QApplication.processEvents()  # Update UI
            
            # Create validator with T-box
            validator = ABoxValidator(tbox_path=self.input_file)
            
            # Validate A-box
            is_consistent, issues = validator.validate(self.abox_data)
            
            # Get validation report
            report = validator.get_validation_report()
            
            # Update validation status
            if is_consistent:
                self.validation_status.setText("✅ Consistent")
                self.validation_status.setStyleSheet("color: green; font-weight: bold;")
                
                # Show success message
                QMessageBox.information(
                    self,
                    "Validation Successful",
                    "✅ The A-box is consistent with the T-box.\n\n" +
                    "No constraint violations were found."
                )
            else:
                self.validation_status.setText("❌ Inconsistent")
                self.validation_status.setStyleSheet("color: red; font-weight: bold;")
                
                # Show detailed error report
                msg = QMessageBox(self)
                msg.setWindowTitle("Validation Failed")
                msg.setIcon(QMessageBox.Icon.Warning)
                msg.setText("❌ The A-box is inconsistent with the T-box.")
                msg.setDetailedText(report)
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                
                # Make the detailed text area larger
                msg.setStyleSheet("QTextEdit { min-width: 600px; min-height: 400px; }")
                
                msg.exec()
            
        except Exception as e:
            self.validation_status.setText("⚠️ Error")
            self.validation_status.setStyleSheet("color: orange;")
            QMessageBox.critical(
                self,
                "Validation Error",
                f"An error occurred during validation:\n\n{str(e)}"
            )
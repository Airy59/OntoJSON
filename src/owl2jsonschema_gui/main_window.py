"""
Main window for the OWL to JSON Schema GUI application.
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
    QSplitter, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QAction, QIcon

# Import the transformation engine
from owl2jsonschema import TransformationEngine, TransformationConfig, OntologyParser


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
                    self.progress.emit("Downloading with requests library...")
                    import tempfile
                    
                    # Download with requests (handles SSL better)
                    # Request RDF/XML or other RDF formats via content negotiation
                    headers = {
                        'Accept': 'application/rdf+xml, text/turtle, application/ld+json, application/n-triples, text/n3;q=0.9, application/xml;q=0.8, */*;q=0.5'
                    }
                    response = requests.get(self.input_source, headers=headers, verify=True, timeout=30)
                    response.raise_for_status()
                    
                    # Detect format from content type
                    content_type = response.headers.get('Content-Type', '').lower()
                    self.progress.emit(f"Content-Type: {content_type}")
                    
                    # Check if we got HTML (common for schema.org and similar sites)
                    content_str = response.content[:1000].decode('utf-8', errors='ignore').lower()
                    
                    # Determine RDF format based on content type or content inspection
                    rdf_format = None
                    suffix = '.rdf'
                    
                    if 'html' in content_type or '<!doctype html' in content_str or '<html' in content_str:
                        # HTML page - might contain embedded JSON-LD
                        self.progress.emit("Detected HTML page, extracting JSON-LD...")
                        
                        # Try to extract JSON-LD from HTML
                        import re
                        json_ld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
                        matches = re.findall(json_ld_pattern, response.text, re.DOTALL | re.IGNORECASE)
                        
                        if matches:
                            # Use the first JSON-LD block found
                            json_ld_content = matches[0]
                            response_content = json_ld_content.encode('utf-8')
                            rdf_format = 'json-ld'
                            suffix = '.jsonld'
                            self.progress.emit(f"Extracted JSON-LD from HTML ({len(json_ld_content)} characters)")
                        else:
                            # No JSON-LD found in HTML
                            raise ValueError(f"The URL {self.input_source} returned HTML without embedded RDF data. "
                                           "Please provide a direct link to an RDF/OWL file.")
                    elif 'json-ld' in content_type or 'application/ld+json' in content_type:
                        rdf_format = 'json-ld'
                        suffix = '.jsonld'
                        response_content = response.content
                    elif 'turtle' in content_type or 'text/turtle' in content_type:
                        rdf_format = 'turtle'
                        suffix = '.ttl'
                        response_content = response.content
                    elif 'n-triples' in content_type:
                        rdf_format = 'nt'
                        suffix = '.nt'
                        response_content = response.content
                    elif 'n3' in content_type or 'text/n3' in content_type:
                        rdf_format = 'n3'
                        suffix = '.n3'
                        response_content = response.content
                    elif 'rdf+xml' in content_type or 'application/rdf+xml' in content_type:
                        rdf_format = 'xml'
                        suffix = '.rdf'
                        response_content = response.content
                    elif 'xml' in content_type and not 'html' in content_type:
                        # Try as RDF/XML
                        rdf_format = 'xml'
                        suffix = '.rdf'
                        response_content = response.content
                    else:
                        # Try to guess from content
                        if content_str.strip().startswith('{') or content_str.strip().startswith('['):
                            # Likely JSON-LD
                            rdf_format = 'json-ld'
                            suffix = '.jsonld'
                        elif content_str.strip().startswith('@'):
                            # Likely Turtle
                            rdf_format = 'turtle'
                            suffix = '.ttl'
                        elif content_str.strip().startswith('<?xml'):
                            # XML - could be RDF/XML
                            rdf_format = 'xml'
                            suffix = '.rdf'
                        else:
                            # Try to guess from URL
                            if self.input_source.endswith('.ttl'):
                                rdf_format = 'turtle'
                                suffix = '.ttl'
                            elif self.input_source.endswith('.jsonld') or self.input_source.endswith('.json'):
                                rdf_format = 'json-ld'
                                suffix = '.jsonld'
                            elif self.input_source.endswith('.nt'):
                                rdf_format = 'nt'
                                suffix = '.nt'
                            elif self.input_source.endswith('.n3'):
                                rdf_format = 'n3'
                                suffix = '.n3'
                        response_content = response.content
                    
                    # Save to temporary file with appropriate extension
                    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
                        tmp_file.write(response_content)
                        tmp_path = tmp_file.name
                    
                    self.progress.emit(f"Parsing ontology (format: {rdf_format or 'auto-detect'})...")
                    parser = OntologyParser()
                    ontology = parser.parse(tmp_path, format=rdf_format)
                    
                    # Clean up temp file
                    import os
                    os.unlink(tmp_path)
                    
                except ImportError:
                    # Requests not available, try urllib with SSL context
                    self.progress.emit("Using urllib with SSL context...")
                    import tempfile
                    import urllib.request
                    import ssl
                    
                    # Create SSL context that handles certificates better
                    ssl_context = ssl.create_default_context()
                    
                    # On macOS, you might need to use system certificates
                    try:
                        import certifi
                        ssl_context.load_verify_locations(certifi.where())
                    except ImportError:
                        # If certifi is not available, try unverified as last resort
                        # (with user warning)
                        if self.input_source.startswith('https://'):
                            self.progress.emit("Warning: SSL certificate verification may be limited")
                            ssl_context.check_hostname = False
                            ssl_context.verify_mode = ssl.CERT_NONE
                    
                    try:
                        # Try downloading with SSL context
                        # Add content negotiation headers
                        req = urllib.request.Request(self.input_source)
                        req.add_header('Accept', 'application/rdf+xml, text/turtle, application/ld+json, application/n-triples, text/n3;q=0.9, application/xml;q=0.8, */*;q=0.5')
                        
                        with urllib.request.urlopen(req, context=ssl_context) as response:
                            content = response.read()
                            content_type = response.headers.get('Content-Type', '').lower()
                            
                        self.progress.emit(f"Content-Type: {content_type}")
                        
                        # Determine format
                        rdf_format = None
                        suffix = '.rdf'
                        
                        if 'json-ld' in content_type or 'application/ld+json' in content_type:
                            rdf_format = 'json-ld'
                            suffix = '.jsonld'
                        elif 'turtle' in content_type or 'text/turtle' in content_type:
                            rdf_format = 'turtle'
                            suffix = '.ttl'
                        elif 'n-triples' in content_type:
                            rdf_format = 'nt'
                            suffix = '.nt'
                        elif 'n3' in content_type:
                            rdf_format = 'n3'
                            suffix = '.n3'
                        
                        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
                            tmp_file.write(content)
                            tmp_path = tmp_file.name
                        
                        self.progress.emit(f"Parsing ontology (format: {rdf_format or 'auto-detect'})...")
                        parser = OntologyParser()
                        ontology = parser.parse(tmp_path, format=rdf_format)
                        
                        # Clean up temp file
                        import os
                        os.unlink(tmp_path)
                    except Exception as download_error:
                        # As a last resort, try letting rdflib handle it directly
                        self.progress.emit("Attempting direct parsing with rdflib...")
                        parser = OntologyParser()
                        ontology = parser.parse(self.input_source)
            else:
                self.progress.emit(f"Parsing ontology from file: {self.input_source}")
                parser = OntologyParser()
                ontology = parser.parse(self.input_source)
            
            self.progress.emit(f"Parsed {len(ontology.classes)} classes, "
                             f"{len(ontology.object_properties)} object properties, "
                             f"{len(ontology.datatype_properties)} datatype properties")
            
            self.progress.emit("Running transformation...")
            config = TransformationConfig(self.config)
            engine = TransformationEngine(config)
            result = engine.transform(ontology)
            
            self.progress.emit("Transformation completed!")
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(f"Error during transformation: {str(e)}\n{traceback.format_exc()}")


class MainWindow(QMainWindow):
    """Main window of the OWL to JSON Schema GUI application."""
    
    def __init__(self):
        super().__init__()
        self.input_file: Optional[str] = None
        self.output_folder: Optional[str] = None
        self.transformation_result: Optional[Dict] = None
        self.rule_checkboxes: Dict[str, QCheckBox] = {}
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("OWL to JSON Schema Converter")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # File selection section
        file_section = self.create_file_section()
        main_layout.addWidget(file_section)
        
        # Create splitter for main content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Configuration
        config_panel = self.create_config_panel()
        splitter.addWidget(config_panel)
        
        # Right panel - Results
        results_panel = self.create_results_panel()
        splitter.addWidget(results_panel)
        
        # Set splitter sizes (40% config, 60% results)
        splitter.setSizes([480, 720])
        
        main_layout.addWidget(splitter)
        
        # Bottom section - Actions and status
        bottom_section = self.create_bottom_section()
        main_layout.addWidget(bottom_section)
        
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
                padding: 5px 15px;
                border-radius: 3px;
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QPushButton#browseButton, QPushButton#outputButton {
                background-color: #008CBA;
            }
            QPushButton#browseButton:hover, QPushButton#outputButton:hover {
                background-color: #007399;
            }
        """)
    
    def create_menu_bar(self):
        """Create the menu bar."""
        menubar = self.menuBar()
        # Ensure menu bar is visible (important for some platforms)
        menubar.setNativeMenuBar(False)  # This ensures the menu bar is shown in the window
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        open_action = QAction("&Open Ontology", self)
        open_action.setShortcut("Ctrl+O")
        open_action.setStatusTip("Open an OWL/RDF ontology file")
        open_action.triggered.connect(self.browse_input_file)
        file_menu.addAction(open_action)
        
        save_action = QAction("&Save JSON Schema", self)
        save_action.setShortcut("Ctrl+S")
        save_action.setStatusTip("Save the generated JSON Schema")
        save_action.triggered.connect(self.save_result)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.setStatusTip("About this application")
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        # Make sure the menu bar is visible
        menubar.setVisible(True)
    
    def create_file_section(self) -> QGroupBox:
        """Create the file selection section."""
        group = QGroupBox("Input/Output Files")
        layout = QVBoxLayout()
        
        # Input file selection
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Input Ontology:"))
        
        self.input_file_label = QLineEdit()
        self.input_file_label.setReadOnly(False)  # Allow manual input for URLs
        self.input_file_label.setPlaceholderText("Enter URL or file path, or browse for file...")
        self.input_file_label.setToolTip("Enter a URL (http://...) or file path, or use Browse button")
        self.input_file_label.textChanged.connect(self.on_input_changed)
        input_layout.addWidget(self.input_file_label)
        
        browse_button = QPushButton("Browse...")
        browse_button.setObjectName("browseButton")
        browse_button.clicked.connect(self.browse_input_file)
        input_layout.addWidget(browse_button)
        
        layout.addLayout(input_layout)
        
        # Output folder selection
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output Folder:"))
        
        self.output_folder_label = QLineEdit()
        self.output_folder_label.setReadOnly(True)
        self.output_folder_label.setPlaceholderText("Select output folder...")
        output_layout.addWidget(self.output_folder_label)
        
        output_button = QPushButton("Browse...")
        output_button.setObjectName("outputButton")
        output_button.clicked.connect(self.browse_output_folder)
        output_layout.addWidget(output_button)
        
        layout.addLayout(output_layout)
        
        group.setLayout(layout)
        return group
    
    def create_config_panel(self) -> QWidget:
        """Create the configuration panel."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Create tabs for different rule categories
        tabs = QTabWidget()
        
        # Class rules tab
        class_tab = self.create_rules_tab("Class Rules", [
            ("class_to_object", "Transform Classes to Objects"),
            ("class_hierarchy", "Transform Class Hierarchy"),
            ("class_restrictions", "Transform Class Restrictions")
        ])
        tabs.addTab(class_tab, "Classes")
        
        # Property rules tab
        property_tab = self.create_rules_tab("Property Rules", [
            ("object_property", "Transform Object Properties"),
            ("datatype_property", "Transform Datatype Properties"),
            ("property_cardinality", "Transform Property Cardinality"),
            ("property_restrictions", "Transform Property Restrictions")
        ])
        tabs.addTab(property_tab, "Properties")
        
        # Annotation rules tab
        annotation_tab = self.create_rules_tab("Annotation Rules", [
            ("labels_to_titles", "Labels to Titles"),
            ("comments_to_descriptions", "Comments to Descriptions"),
            ("annotations_to_metadata", "Annotations to Metadata")
        ])
        tabs.addTab(annotation_tab, "Annotations")
        
        # Advanced rules tab
        advanced_tab = self.create_rules_tab("Advanced Rules", [
            ("enumeration_to_enum", "Enumerations to Enum"),
            ("union_to_anyOf", "Unions to anyOf"),
            ("intersection_to_allOf", "Intersections to allOf"),
            ("complement_to_not", "Complement to not"),
            ("equivalent_classes", "Equivalent Classes"),
            ("disjoint_classes", "Disjoint Classes")
        ])
        tabs.addTab(advanced_tab, "Advanced")
        
        # Structural rules tab
        structural_tab = self.create_rules_tab("Structural Rules", [
            ("ontology_to_document", "Ontology to Document"),
            ("individuals_to_examples", "Individuals to Examples"),
            ("ontology_metadata", "Ontology Metadata")
        ])
        tabs.addTab(structural_tab, "Structural")
        
        # Options tab
        options_tab = self.create_options_tab()
        tabs.addTab(options_tab, "Options")
        
        layout.addWidget(tabs)
        
        # Quick actions
        actions_layout = QHBoxLayout()
        
        select_all_button = QPushButton("Select All")
        select_all_button.clicked.connect(self.select_all_rules)
        actions_layout.addWidget(select_all_button)
        
        deselect_all_button = QPushButton("Deselect All")
        deselect_all_button.clicked.connect(self.deselect_all_rules)
        actions_layout.addWidget(deselect_all_button)
        
        layout.addLayout(actions_layout)
        
        widget.setLayout(layout)
        return widget
    
    def create_rules_tab(self, title: str, rules: list) -> QWidget:
        """Create a tab for a group of transformation rules."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        for rule_id, rule_name in rules:
            checkbox = QCheckBox(rule_name)
            checkbox.setChecked(True)  # Default to enabled
            self.rule_checkboxes[rule_id] = checkbox
            scroll_layout.addWidget(checkbox)
        
        scroll_layout.addStretch()
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        
        layout.addWidget(scroll)
        widget.setLayout(layout)
        return widget
    
    def create_options_tab(self) -> QWidget:
        """Create the options tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Language option
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Language for labels/comments:"))
        self.language_combo = QComboBox()
        self.language_combo.addItems(["en", "fr", "de", "es", "it"])
        lang_layout.addWidget(self.language_combo)
        lang_layout.addStretch()
        layout.addLayout(lang_layout)
        
        # Indentation option
        indent_layout = QHBoxLayout()
        indent_layout.addWidget(QLabel("JSON indentation:"))
        self.indent_spin = QSpinBox()
        self.indent_spin.setRange(0, 8)
        self.indent_spin.setValue(2)
        indent_layout.addWidget(self.indent_spin)
        indent_layout.addStretch()
        layout.addLayout(indent_layout)
        
        # Output format
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Output format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["JSON", "YAML"])
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        layout.addLayout(format_layout)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_results_panel(self) -> QWidget:
        """Create the results panel."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Results tabs
        self.results_tabs = QTabWidget()
        
        # JSON Schema output tab
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Courier", 10))
        self.results_tabs.addTab(self.output_text, "JSON Schema Output")
        
        # Statistics tab
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.stats_table.horizontalHeader().setStretchLastSection(True)
        self.results_tabs.addTab(self.stats_table, "Statistics")
        
        # Log tab
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier", 9))
        self.results_tabs.addTab(self.log_text, "Log")
        
        layout.addWidget(self.results_tabs)
        
        widget.setLayout(layout)
        return widget
    
    def create_bottom_section(self) -> QWidget:
        """Create the bottom section with actions and status."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.transform_button = QPushButton("Transform")
        self.transform_button.clicked.connect(self.run_transformation)
        self.transform_button.setEnabled(False)
        button_layout.addWidget(self.transform_button)
        
        self.save_button = QPushButton("Save Result")
        self.save_button.clicked.connect(self.save_result)
        self.save_button.setEnabled(False)
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
        
        widget.setLayout(layout)
        return widget
    
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
            self.input_file_label.setText(file_path)
            self.transform_button.setEnabled(True)
            self.log_message(f"Selected input file: {file_path}")
    
    def on_input_changed(self, text: str):
        """Handle changes to the input field."""
        text = text.strip()
        if text:
            self.input_file = text
            self.transform_button.setEnabled(True)
            
            # Log whether it's a URL or file path
            if text.startswith(('http://', 'https://', 'ftp://')):
                self.log_message(f"Input URL: {text}")
            else:
                self.log_message(f"Input path: {text}")
        else:
            self.input_file = None
            self.transform_button.setEnabled(False)
    
    def browse_output_folder(self):
        """Browse for output folder."""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            ""
        )
        
        if folder_path:
            self.output_folder = folder_path
            self.output_folder_label.setText(folder_path)
            self.log_message(f"Selected output folder: {folder_path}")
    
    def select_all_rules(self):
        """Select all transformation rules."""
        for checkbox in self.rule_checkboxes.values():
            checkbox.setChecked(True)
    
    def deselect_all_rules(self):
        """Deselect all transformation rules."""
        for checkbox in self.rule_checkboxes.values():
            checkbox.setChecked(False)
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get the current configuration from the GUI."""
        config = {
            "rules": {},
            "output": {
                "format": "json-schema-draft-07",
                "indent": self.indent_spin.value()
            }
        }
        
        # Get rule configurations
        for rule_id, checkbox in self.rule_checkboxes.items():
            config["rules"][rule_id] = {
                "enabled": checkbox.isChecked(),
                "options": {}
            }
        
        # Add language option for annotation rules
        language = self.language_combo.currentText()
        if "labels_to_titles" in config["rules"]:
            config["rules"]["labels_to_titles"]["options"]["language"] = language
        if "comments_to_descriptions" in config["rules"]:
            config["rules"]["comments_to_descriptions"]["options"]["language"] = language
        
        return config
    
    def run_transformation(self):
        """Run the transformation."""
        if not self.input_file:
            QMessageBox.warning(self, "Warning", "Please enter a URL or select an input file first.")
            return
        
        # Validate URL if it looks like one
        input_source = self.input_file.strip()
        if input_source.startswith(('http://', 'https://', 'ftp://')):
            self.log_message(f"Starting transformation from URL: {input_source}")
        else:
            # Check if local file exists
            from pathlib import Path
            if not Path(input_source).exists():
                QMessageBox.warning(self, "Warning", f"File not found: {input_source}")
                return
            self.log_message(f"Starting transformation from file: {input_source}")
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.transform_button.setEnabled(False)
        self.save_button.setEnabled(False)
        
        # Get configuration
        config = self.get_configuration()
        
        # Create and start worker thread
        self.worker = TransformationWorker(self.input_file, config)
        self.worker.progress.connect(self.on_progress)
        self.worker.error.connect(self.on_error)
        self.worker.finished.connect(self.on_transformation_complete)
        self.worker.start()
    
    def on_progress(self, message: str):
        """Handle progress updates."""
        self.log_message(message)
        self.status_label.setText(message)
    
    def on_error(self, error_message: str):
        """Handle transformation errors."""
        self.log_message(f"ERROR: {error_message}")
        self.progress_bar.setVisible(False)
        self.transform_button.setEnabled(True)
        QMessageBox.critical(self, "Transformation Error", error_message)
    
    def on_transformation_complete(self, result: Dict):
        """Handle transformation completion."""
        self.transformation_result = result
        
        # Display result
        if self.format_combo.currentText() == "YAML":
            import yaml
            output_text = yaml.dump(result, default_flow_style=False, sort_keys=False)
        else:
            output_text = json.dumps(result, indent=self.indent_spin.value())
        
        self.output_text.setPlainText(output_text)
        
        # Update statistics
        self.update_statistics(result)
        
        # Update UI
        self.progress_bar.setVisible(False)
        self.transform_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.status_label.setText("Transformation completed successfully!")
        self.log_message("Transformation completed!")
        
        # Switch to output tab
        self.results_tabs.setCurrentIndex(0)
    
    def update_statistics(self, result: Dict):
        """Update the statistics table."""
        stats = []
        
        # Count definitions
        if "definitions" in result:
            stats.append(("Definitions", str(len(result["definitions"]))))
        
        # Count properties
        if "properties" in result:
            stats.append(("Root Properties", str(len(result["properties"]))))
        
        # Count examples
        if "examples" in result:
            stats.append(("Examples", str(len(result["examples"]))))
        
        # Schema version
        if "$schema" in result:
            stats.append(("Schema Version", result["$schema"]))
        
        # Update table
        self.stats_table.setRowCount(len(stats))
        for i, (key, value) in enumerate(stats):
            self.stats_table.setItem(i, 0, QTableWidgetItem(key))
            self.stats_table.setItem(i, 1, QTableWidgetItem(value))
    
    def save_result(self):
        """Save the transformation result."""
        if not self.transformation_result:
            QMessageBox.warning(self, "Warning", "No transformation result to save.")
            return
        
        # Determine default filename
        if self.input_file:
            base_name = Path(self.input_file).stem
            default_name = f"{base_name}_schema.json"
        else:
            default_name = "schema.json"
        
        # Get save location
        if self.output_folder:
            default_path = str(Path(self.output_folder) / default_name)
        else:
            default_path = default_name
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save JSON Schema",
            default_path,
            "JSON Files (*.json);;YAML Files (*.yaml *.yml);;All Files (*.*)"
        )
        
        if file_path:
            try:
                path = Path(file_path)
                
                if path.suffix in ['.yaml', '.yml'] or self.format_combo.currentText() == "YAML":
                    import yaml
                    content = yaml.dump(self.transformation_result, default_flow_style=False, sort_keys=False)
                else:
                    content = json.dumps(self.transformation_result, indent=self.indent_spin.value())
                
                path.write_text(content)
                self.log_message(f"Saved result to: {file_path}")
                QMessageBox.information(self, "Success", f"Schema saved to:\n{file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save file:\n{str(e)}")
    
    def log_message(self, message: str):
        """Add a message to the log."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About OWL to JSON Schema Converter",
            "Version 0.1 - August 2025\n\n"
            "© Airy Magnien (Airy59 on GitHub)\n\n"
            "https://github.com/airymagnien/owl2jsonschema"
        )
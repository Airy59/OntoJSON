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
    QSplitter, QProgressBar, QStatusBar, QFrame, QApplication, QDialog,
    QDialogButtonBox, QGridLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QAction, QIcon, QPixmap

# Import the transformation engine and A-box generator
from owl2jsonschema import TransformationEngine, TransformationConfig, OntologyParser, ABoxGenerator
from owl2jsonschema.reasoner import ABoxValidator


class RulesConfigDialog(QDialog):
    """Dialog for configuring transformation rules."""
    
    def __init__(self, parent=None, current_config=None):
        super().__init__(parent)
        self.setWindowTitle("Transformation Rules Configuration")
        self.setMinimumSize(700, 600)
        
        # Merge current configuration with defaults to ensure all fields are present
        default_config = self.get_default_config()
        if current_config:
            # Merge the enabled states from current_config into default_config
            for rule_id, rule_settings in current_config.items():
                if rule_id in default_config:
                    default_config[rule_id]["enabled"] = rule_settings.get("enabled", False)
        self.config = default_config
        
        # Create the UI
        self.init_ui()
        
    def get_default_config(self):
        """Get default configuration for all rules."""
        return {
            # Class Transformations
            "class_to_object": {"enabled": True, "name": "OWL Class to JSON Object",
                              "description": "Transform OWL classes into JSON Schema object types"},
            "class_hierarchy": {"enabled": True, "name": "Class Hierarchy to JSON Schema Inheritance",
                              "description": "Transform subclass relationships using allOf"},
            "class_restrictions": {"enabled": True, "name": "Class Restrictions to JSON Schema Constraints",
                                  "description": "Transform OWL restrictions into JSON Schema constraints"},
            
            # Property Transformations
            "object_property": {"enabled": True, "name": "OWL Object Property to JSON Property",
                              "description": "Transform object properties with proper references"},
            "datatype_property": {"enabled": True, "name": "OWL Datatype Property to JSON Property",
                                "description": "Transform datatype properties with appropriate types"},
            "property_cardinality": {"enabled": True, "name": "Property Cardinality to JSON Constraints",
                                   "description": "Transform cardinality restrictions to minItems/maxItems"},
            "property_restrictions": {"enabled": True, "name": "Property Restrictions to JSON Validation",
                                    "description": "Transform property restrictions to validation rules"},
            
            # Annotation Transformations
            "labels_to_titles": {"enabled": True, "name": "RDFS Labels to JSON Schema Titles",
                               "description": "Convert rdfs:label to JSON Schema title"},
            "comments_to_descriptions": {"enabled": True, "name": "RDFS Comments to JSON Descriptions",
                                        "description": "Convert rdfs:comment to JSON Schema description"},
            "annotations_to_metadata": {"enabled": False, "name": "Other Annotations to JSON Metadata",
                                       "description": "Convert other annotations to custom metadata"},
            
            # Advanced Transformations
            "enumeration_to_enum": {"enabled": True, "name": "OWL Enumeration to JSON Schema Enum",
                                  "description": "Convert owl:oneOf to JSON Schema enum"},
            "union_to_anyOf": {"enabled": True, "name": "OWL Union to JSON Schema anyOf",
                             "description": "Convert owl:unionOf to JSON Schema anyOf"},
            "intersection_to_allOf": {"enabled": True, "name": "OWL Intersection to JSON Schema allOf",
                                    "description": "Convert owl:intersectionOf to JSON Schema allOf"},
            "complement_to_not": {"enabled": False, "name": "OWL Complement to JSON Schema not",
                                "description": "Convert owl:complementOf to JSON Schema not"},
            "equivalent_classes": {"enabled": True, "name": "OWL Equivalent Classes to Definitions",
                                 "description": "Handle equivalent class relationships"},
            "disjoint_classes": {"enabled": True, "name": "OWL Disjoint Union to oneOf",
                               "description": "Transform disjoint class unions into JSON Schema oneOf constraints"},
            
            # Structural Transformations
            "ontology_to_document": {"enabled": True, "name": "Ontology to JSON Schema Document",
                                   "description": "Transform ontology structure to JSON Schema document"},
            "individuals_to_examples": {"enabled": False, "name": "Named Individuals to JSON Examples",
                                       "description": "Convert named individuals to JSON Schema examples"},
            "ontology_metadata": {"enabled": True, "name": "Ontology Metadata to JSON Metadata",
                                "description": "Preserve ontology metadata in JSON Schema"},
            "thing_with_uri": {"enabled": True, "name": "Add Base Object with URI Property",
                              "description": "Add a base _Thing object with 'uri' property that all classes inherit from (for RDF stream compatibility)"}
        }
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        
        # Description
        desc_label = QLabel("Configure which transformation rules should be applied when converting OWL to JSON Schema.")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        layout.addWidget(desc_label)
        
        # Create scrollable area for rules
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # Group rules by category
        categories = {
            "Class Transformations": ["class_to_object", "class_hierarchy", "class_restrictions"],
            "Property Transformations": ["object_property", "datatype_property", "property_cardinality", "property_restrictions"],
            "Annotation Transformations": ["labels_to_titles", "comments_to_descriptions", "annotations_to_metadata"],
            "Advanced Transformations": ["enumeration_to_enum", "union_to_anyOf", "intersection_to_allOf",
                                        "complement_to_not", "equivalent_classes", "disjoint_classes"],
            "Structural Transformations": ["ontology_to_document", "individuals_to_examples", "ontology_metadata", "thing_with_uri"]
        }
        
        self.checkboxes = {}
        
        for category, rule_ids in categories.items():
            # Create category group
            group = QGroupBox(category)
            group_layout = QVBoxLayout()
            
            for rule_id in rule_ids:
                if rule_id in self.config:
                    rule_config = self.config[rule_id]
                    
                    # Create checkbox with description
                    checkbox = QCheckBox(rule_config["name"])
                    checkbox.setChecked(rule_config.get("enabled", False))
                    checkbox.setToolTip(rule_config.get("description", ""))
                    
                    # Store reference
                    self.checkboxes[rule_id] = checkbox
                    
                    # Add description label
                    desc = QLabel(f"  {rule_config.get('description', '')}")
                    desc.setWordWrap(True)
                    desc.setStyleSheet("color: #666; margin-left: 20px; margin-bottom: 5px;")
                    
                    group_layout.addWidget(checkbox)
                    group_layout.addWidget(desc)
            
            group.setLayout(group_layout)
            scroll_layout.addWidget(group)
        
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # Quick action buttons
        button_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all)
        button_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all)
        button_layout.addWidget(deselect_all_btn)
        
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        
        # Save/Load configuration buttons
        save_config_btn = QPushButton("Save Configuration")
        save_config_btn.clicked.connect(self.save_configuration)
        button_layout.addWidget(save_config_btn)
        
        load_config_btn = QPushButton("Load Configuration")
        load_config_btn.clicked.connect(self.load_configuration)
        button_layout.addWidget(load_config_btn)
        
        layout.addLayout(button_layout)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def select_all(self):
        """Select all rules."""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(True)
    
    def deselect_all(self):
        """Deselect all rules."""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)
    
    def reset_to_defaults(self):
        """Reset to default configuration."""
        default_config = self.get_default_config()
        for rule_id, checkbox in self.checkboxes.items():
            if rule_id in default_config:
                checkbox.setChecked(default_config[rule_id].get("enabled", False))
    
    def get_configuration(self):
        """Get the current configuration from the dialog."""
        # Return the full configuration with all fields
        config = {}
        for rule_id, checkbox in self.checkboxes.items():
            if rule_id in self.config:
                # Copy the full configuration including name and description
                config[rule_id] = self.config[rule_id].copy()
                # Update the enabled state from the checkbox
                config[rule_id]["enabled"] = checkbox.isChecked()
            else:
                # Fallback if the rule is not in the config
                config[rule_id] = {"enabled": checkbox.isChecked()}
        return config
    
    def save_configuration(self):
        """Save the current configuration to a JSON file."""
        from PyQt6.QtWidgets import QFileDialog
        import json
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Configuration",
            "owl2jsonschema_config.json",
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if file_path:
            try:
                # Get current configuration
                config = {}
                for rule_id, checkbox in self.checkboxes.items():
                    if rule_id in self.config:
                        config[rule_id] = {
                            "enabled": checkbox.isChecked(),
                            "name": self.config[rule_id].get("name", ""),
                            "description": self.config[rule_id].get("description", "")
                        }
                
                # Save to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2)
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"Configuration saved to:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Save Error",
                    f"Failed to save configuration:\n{str(e)}"
                )
    
    def load_configuration(self):
        """Load configuration from a JSON file."""
        from PyQt6.QtWidgets import QFileDialog
        import json
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Configuration",
            "",
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if file_path:
            try:
                # Load configuration from file
                with open(file_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                
                # Update checkboxes based on loaded configuration
                for rule_id, rule_settings in loaded_config.items():
                    if rule_id in self.checkboxes:
                        self.checkboxes[rule_id].setChecked(rule_settings.get("enabled", False))
                        
                        # Update the internal config with loaded values
                        if rule_id in self.config:
                            self.config[rule_id]["enabled"] = rule_settings.get("enabled", False)
                            # Optionally update name and description if they exist
                            if "name" in rule_settings:
                                self.config[rule_id]["name"] = rule_settings["name"]
                            if "description" in rule_settings:
                                self.config[rule_id]["description"] = rule_settings["description"]
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"Configuration loaded from:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Load Error",
                    f"Failed to load configuration:\n{str(e)}"
                )


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
        
        # Transformation rules configuration
        self.rules_config = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("OWL to JSON Schema Transformer - T-box/A-box Workflow")
        self.setGeometry(100, 100, 1400, 900)
        
        # Set application icon
        try:
            # Try to load the high-resolution icon
            icon_path = Path("Resources/ORW_big.png")
            if not icon_path.exists():
                # Try alternative path (in case we're running from a different directory)
                icon_path = Path(__file__).parent.parent.parent / "Resources" / "ORW_big.png"
            
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
            else:
                # Fallback to low-res icon
                icon_path = Path("Resources/ORW_48.png")
                if not icon_path.exists():
                    icon_path = Path(__file__).parent.parent.parent / "Resources" / "ORW_48.png"
                if icon_path.exists():
                    self.setWindowIcon(QIcon(str(icon_path)))
        except Exception as e:
            print(f"Could not set application icon: {e}")
        
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
        
        save_ontology_action = QAction("Save &Ontology to...", self)
        save_ontology_action.setShortcut("Ctrl+Shift+S")
        save_ontology_action.triggered.connect(self.save_ontology_as)
        save_ontology_action.setEnabled(False)
        self.save_ontology_action = save_ontology_action
        file_menu.addAction(save_ontology_action)
        
        file_menu.addSeparator()
        
        save_schema_action = QAction("Save JSON &Schema...", self)
        save_schema_action.setShortcut("Ctrl+S")
        save_schema_action.triggered.connect(self.save_schema)
        save_schema_action.setEnabled(False)
        self.save_schema_action = save_schema_action
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
        
        credits_action = QAction("&Credits", self)
        credits_action.triggered.connect(self.show_credits)
        help_menu.addAction(credits_action)
    
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
        self.file_label.setStyleSheet("""
            QLabel {
                padding: 5px;
                background-color: #f8f8f8;
                border: 1px solid #ddd;
                border-radius: 3px;
            }
        """)
        input_layout.addWidget(self.file_label)
        
        open_btn = QPushButton("📁 Open OWL File")
        open_btn.clicked.connect(self.browse_input_file)
        open_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        input_layout.addWidget(open_btn)
        
        url_btn = QPushButton("🌐 Open from URL")
        url_btn.clicked.connect(self.open_url)
        url_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        input_layout.addWidget(url_btn)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # Configuration section
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout()
        
        # Language selection
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Language:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["en", "fr", "de", "es"])
        lang_layout.addWidget(self.lang_combo)
        lang_layout.addStretch()
        config_layout.addLayout(lang_layout)
        
        # Output options
        self.include_uri_check = QCheckBox("Include OWL class and property URIs in schema")
        self.include_uri_check.setToolTip("Add OWL class and property URIs as metadata ($comment) in the JSON Schema")
        config_layout.addWidget(self.include_uri_check)
        
        # Rules configuration button
        rules_btn_layout = QHBoxLayout()
        self.rules_status_label = QLabel("20 transformation rules configured")
        self.rules_status_label.setStyleSheet("color: #666;")
        rules_btn_layout.addWidget(self.rules_status_label)
        rules_btn_layout.addStretch()
        
        configure_rules_btn = QPushButton("Configure Transformation Rules...")
        configure_rules_btn.clicked.connect(self.configure_rules)
        configure_rules_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        rules_btn_layout.addWidget(configure_rules_btn)
        
        config_layout.addLayout(rules_btn_layout)
        
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
            self.save_ontology_action.setEnabled(True)  # Enable save ontology menu item
            
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
            self.save_ontology_action.setEnabled(True)  # Enable save ontology menu item
            self.input_text.setPlainText(f"URL: {url}\n\n(Content will be loaded during transformation)")
    
    def configure_rules(self):
        """Open the rules configuration dialog."""
        dialog = RulesConfigDialog(self, self.rules_config)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.rules_config = dialog.get_configuration()
            # Update status label
            enabled_count = sum(1 for rule in self.rules_config.values() if rule.get("enabled", False))
            self.rules_status_label.setText(f"{enabled_count} of 20 rules enabled")
    
    def run_transformation(self):
        """Run the T-box transformation."""
        if not self.input_file:
            QMessageBox.warning(self, "Warning", "Please select an input file first.")
            return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.transform_btn.setEnabled(False)
        
        # Get rules configuration (use defaults if not configured)
        if self.rules_config is None:
            dialog = RulesConfigDialog(self)
            self.rules_config = dialog.get_default_config()
            enabled_count = sum(1 for rule in self.rules_config.values() if rule.get("enabled", False))
            self.rules_status_label.setText(f"{enabled_count} of 20 rules enabled")
        
        # Build configuration with all rules
        rules_config = {}
        for rule_id, rule_settings in self.rules_config.items():
            if rule_id == "labels_to_titles":
                # Special case for labels_to_titles which needs language option
                rules_config[rule_id] = {
                    "enabled": rule_settings.get("enabled", False),
                    "options": {"language": self.lang_combo.currentText()}
                }
            elif rule_id == "disjoint_classes":
                # Special case for disjoint_classes which needs enforcement option
                rules_config[rule_id] = {
                    "enabled": rule_settings.get("enabled", False),
                    "options": {"enforcement": "oneOf"}
                }
            else:
                rules_config[rule_id] = {"enabled": rule_settings.get("enabled", False)}
        
        # Get configuration
        config = {
            "rules": rules_config,
            "output": {
                "include_uri": self.include_uri_check.isChecked(),
                "use_arrays": True  # Always use arrays for multi-valued properties
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
        self.save_schema_action.setEnabled(True)  # Enable save schema action
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
            "© 2024 Airy Magnien\n"
            "Licensed under the European Union Public Licence (EUPL) v1.2"
        )
    
    def show_credits(self):
        """Show credits dialog."""
        # Try to read the credits file from multiple possible locations
        credits_text = ""
        credits_file = None
        
        # Try multiple locations for the credits file
        possible_locations = [
            Path("credits.txt"),  # Current working directory
            Path(__file__).parent.parent.parent / "credits.txt",  # Project root (relative to this file)
            Path(__file__).parent / "credits.txt",  # Same directory as this file
            Path.cwd() / "credits.txt",  # Explicit current working directory
        ]
        
        # Find the first existing credits file
        for location in possible_locations:
            if location.exists():
                credits_file = location
                break
        
        if credits_file and credits_file.exists():
            try:
                with open(credits_file, 'r', encoding='utf-8') as f:
                    credits_text = f.read()
            except Exception as e:
                credits_text = f"Error reading credits file: {str(e)}\n\n"
                credits_text += f"Attempted to read from: {credits_file}\n"
                credits_text += "Please ensure credits.txt is accessible."
        else:
            credits_text = "Credits file not found.\n\n"
            credits_text += "Searched in the following locations:\n"
            for location in possible_locations:
                credits_text += f"  - {location.resolve()}\n"
            credits_text += "\nPlease ensure credits.txt exists in one of these locations\n"
            credits_text += "with the following information:\n\n"
            credits_text += "- Third-party libraries and their licenses\n"
            credits_text += "- Contributors and acknowledgments\n"
            credits_text += "- Any other relevant credits"
        
        # Create a scrollable dialog for credits
        dialog = QDialog(self)
        dialog.setWindowTitle("Credits")
        dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout()
        
        # Create a text edit widget for displaying credits
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(credits_text)
        text_edit.setFont(QFont("Courier", 10))
        
        layout.addWidget(text_edit)
        
        # Add a close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.close)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        dialog.exec()
    
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
    
    def save_ontology_as(self):
        """Save the loaded ontology in a different format."""
        if not self.input_file:
            QMessageBox.warning(self, "Warning", "No ontology loaded. Please open an ontology file first.")
            return
        
        # Create format selection dialog
        from PyQt6.QtWidgets import QInputDialog
        
        formats = [
            "RDF/XML (.rdf, .owl)",
            "Turtle (.ttl)",
            "N-Triples (.nt)",
            "JSON-LD (.jsonld)",
            "N3 (.n3)",
            "Functional Syntax (.ofn)",
            "Manchester Syntax (.omn)"
        ]
        
        format_choice, ok = QInputDialog.getItem(
            self,
            "Select Format",
            "Choose the format to save the ontology:",
            formats,
            0,  # Default to RDF/XML
            False  # Not editable
        )
        
        if not ok:
            return
        
        # Map user choice to format and extension
        format_map = {
            "RDF/XML (.rdf, .owl)": ("xml", ".rdf"),
            "Turtle (.ttl)": ("turtle", ".ttl"),
            "N-Triples (.nt)": ("nt", ".nt"),
            "JSON-LD (.jsonld)": ("json-ld", ".jsonld"),
            "N3 (.n3)": ("n3", ".n3"),
            "Functional Syntax (.ofn)": ("xml", ".ofn"),  # Note: rdflib doesn't support OWL functional syntax directly
            "Manchester Syntax (.omn)": ("xml", ".omn")    # Note: rdflib doesn't support Manchester syntax directly
        }
        
        rdf_format, file_ext = format_map[format_choice]
        
        # Special handling for functional and Manchester syntax
        if format_choice in ["Functional Syntax (.ofn)", "Manchester Syntax (.omn)"]:
            QMessageBox.information(
                self,
                "Format Note",
                f"{format_choice.split(' ')[0]} is not directly supported by the RDF library.\n"
                "The ontology will be saved in RDF/XML format with the appropriate extension.\n"
                "You may need to use specialized OWL tools to convert to this format."
            )
        
        # Get save file path
        suggested_name = "ontology" + file_ext
        if isinstance(self.input_file, str) and not self.input_file.startswith(('http://', 'https://')):
            base_name = Path(self.input_file).stem
            suggested_name = base_name + file_ext
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Save Ontology as {format_choice.split(' ')[0]}",
            suggested_name,
            f"{format_choice.split('(')[0].strip()} (*{file_ext});;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            # Parse the ontology if not already parsed
            from rdflib import Graph
            
            self.status_message.setText("Loading ontology for conversion...")
            QApplication.processEvents()
            
            g = Graph()
            
            # Load the ontology
            if self.input_file.startswith(('http://', 'https://')):
                # Load from URL
                g.parse(self.input_file)
            else:
                # Load from file
                g.parse(self.input_file)
            
            self.status_message.setText(f"Saving as {format_choice.split(' ')[0]}...")
            QApplication.processEvents()
            
            # Serialize in the requested format
            serialized = g.serialize(format=rdf_format)
            
            # Write to file
            if isinstance(serialized, bytes):
                with open(file_path, 'wb') as f:
                    f.write(serialized)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(serialized)
            
            self.status_message.setText("Ontology saved successfully!")
            
            QMessageBox.information(
                self,
                "Success",
                f"Ontology saved successfully to:\n{file_path}\n\nFormat: {format_choice.split(' ')[0]}"
            )
            
        except Exception as e:
            self.status_message.setText("Failed to save ontology")
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save ontology:\n\n{str(e)}"
            )
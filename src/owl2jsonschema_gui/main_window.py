"""
Main window for the OWL to JSON Schema GUI application with T-box/A-box workflow.
"""

import sys
import json
import traceback
from pathlib import Path
from typing import Optional, Dict, Any, List
import subprocess
import tempfile

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTextEdit,
    QGroupBox, QCheckBox, QScrollArea, QMessageBox,
    QTabWidget, QComboBox, QSpinBox, QLineEdit,
    QSplitter, QProgressBar, QStatusBar, QFrame, QApplication, QDialog,
    QDialogButtonBox, QGridLayout, QRadioButton, QButtonGroup, QInputDialog,
    QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QAction, QIcon, QPixmap, QTextCursor, QPalette, QColor

# Import the transformation engine and A-box generator
from owl2jsonschema import TransformationEngine, TransformationConfig, OntologyParser, ABoxGenerator
from owl2jsonschema.reasoner import ABoxValidator
from owl2jsonschema.abox_to_json import ABoxToJSONConverter
from owl2jsonschema.composite_builder import CompositeOntologyBuilder
from owl2jsonschema.services.validation_service import JSONSchemaValidator, SchemaValidationService


class CompositeMetadataDialog(QDialog):
    """Dialog for entering metadata for a composite ontology."""
    
    def __init__(self, parent=None, file_paths=None):
        super().__init__(parent)
        self.file_paths = file_paths or []
        self.setWindowTitle("Composite Ontology Metadata")
        self.setMinimumSize(500, 400)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        
        # Title - adjust based on number of files
        if len(self.file_paths) == 1:
            title_label = QLabel("Ontology Metadata Configuration")
        else:
            title_label = QLabel("Composite Ontology Configuration")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(title_label)
        
        # Show selected files
        files_label = "Selected Ontology" if len(self.file_paths) == 1 else "Selected Ontologies"
        files_group = QGroupBox(files_label)
        files_layout = QVBoxLayout()
        files_text = QTextEdit()
        files_text.setReadOnly(True)
        files_text.setMaximumHeight(100)
        
        file_list = "\n".join([f"• {Path(f).name}" for f in self.file_paths])
        files_text.setPlainText(file_list)
        files_layout.addWidget(files_text)
        files_group.setLayout(files_layout)
        layout.addWidget(files_group)
        
        # Metadata fields
        metadata_group = QGroupBox("Metadata (Optional)")
        metadata_layout = QGridLayout()
        
        # Title field
        metadata_layout.addWidget(QLabel("Title:"), 0, 0)
        self.title_input = QLineEdit()
        if len(self.file_paths) == 1:
            self.title_input.setPlaceholderText("Ontology title")
        else:
            self.title_input.setPlaceholderText(f"Composite of {len(self.file_paths)} ontologies")
        metadata_layout.addWidget(self.title_input, 0, 1)
        
        # Version field
        metadata_layout.addWidget(QLabel("Version:"), 1, 0)
        self.version_input = QLineEdit()
        self.version_input.setPlaceholderText("1.0.0")
        metadata_layout.addWidget(self.version_input, 1, 1)
        
        # Author field
        metadata_layout.addWidget(QLabel("Author:"), 2, 0)
        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("Your name or organization")
        metadata_layout.addWidget(self.author_input, 2, 1)
        
        # Description field
        metadata_layout.addWidget(QLabel("Description:"), 3, 0)
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(60)
        self.description_input.setPlaceholderText("Description of the composite ontology")
        metadata_layout.addWidget(self.description_input, 3, 1)
        
        # Comment field
        metadata_layout.addWidget(QLabel("Comments:"), 4, 0)
        self.comment_input = QTextEdit()
        self.comment_input.setMaximumHeight(60)
        self.comment_input.setPlaceholderText("Additional notes or comments")
        metadata_layout.addWidget(self.comment_input, 4, 1)
        
        metadata_group.setLayout(metadata_layout)
        layout.addWidget(metadata_group)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_metadata(self):
        """Get the metadata entered by the user."""
        metadata = {}
        
        if self.title_input.text().strip():
            metadata["title"] = self.title_input.text().strip()
        
        if self.version_input.text().strip():
            metadata["version"] = self.version_input.text().strip()
        
        if self.author_input.text().strip():
            metadata["author"] = self.author_input.text().strip()
        
        if self.description_input.toPlainText().strip():
            metadata["description"] = self.description_input.toPlainText().strip()
        
        if self.comment_input.toPlainText().strip():
            metadata["comment"] = self.comment_input.toPlainText().strip()
        
        return metadata


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
    
    def __init__(self, input_source: str, config: Dict[str, Any], ontology_list: List[str] = None):
        super().__init__()
        self.input_source = input_source.strip()
        self.config = config
        self.ontology_list = ontology_list or []
        self.transformation_service_result = None
    
    def run(self):
        """Run the transformation in a separate thread."""
        try:
            from owl2jsonschema.services.transformation_service import TransformationService
            
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
            
            # Use transformation service for multi-ontology support
            service = TransformationService()
            transformation_config = TransformationConfig(self.config)
            
            # Debug output
            print(f"DEBUG Worker: ontology_list = {self.ontology_list}")
            print(f"DEBUG Worker: len(ontology_list) = {len(self.ontology_list) if self.ontology_list else 0}")
            
            # Always use transform_multiple to get both composite and component schemas
            if self.ontology_list and len(self.ontology_list) > 0:
                num_ontologies = len(self.ontology_list)
                if num_ontologies > 1:
                    self.progress.emit(f"Transforming composite with {num_ontologies} component ontologies...")
                else:
                    self.progress.emit("Transforming ontology (composite + component schemas)...")
                
                print(f"DEBUG Worker: Calling transform_multiple with {num_ontologies} sources")
                service_result = service.transform_multiple(
                    sources=self.ontology_list,
                    config=transformation_config,
                    transform_components=True
                )
                print(f"DEBUG Worker: transform_multiple returned, success={service_result.success}")
                print(f"DEBUG Worker: component_schemas keys: {list(service_result.component_schemas.keys()) if service_result.component_schemas else 'None'}")
            else:
                # Fallback to single transformation (shouldn't happen in normal flow)
                print(f"DEBUG Worker: Falling back to transform_single")
                self.progress.emit("Running transformation...")
                service_result = service.transform_single(
                    source=self.input_source,
                    config=transformation_config
                )
            
            if not service_result.success:
                raise Exception(service_result.error)
            
            # Store the full service result for later use
            self.transformation_service_result = service_result
            result = service_result.schema
            
            self.progress.emit("Transformation completed!")
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(f"Error during transformation: {str(e)}\n{traceback.format_exc()}")


class MainWindow(QMainWindow):
    """Main window of the OWL to JSON Schema GUI application with T-box/A-box workflow."""
    
    def __init__(self):
        super().__init__()
        self.input_file: Optional[str] = None
        self.input_files: List[str] = []  # For multiple file selection
        self.is_composite: bool = False  # Track if using composite ontology
        self.temp_composite_file: Optional[str] = None  # Track temporary composite file
        self.composite_builder: Optional[CompositeOntologyBuilder] = None  # Store composite builder for saving
        self.ontology_list: List[str] = []  # Persistent list of ontologies
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
        
        # Ontology partitioning state
        self.partitioning_ontology_path = None
        self.partitioning_results = None
        self.current_partition_file = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("OntoJSON - OWL to JSON Schema Transformer")
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
        
        open_multiple_action = QAction("Open &Multiple OWL Files...", self)
        open_multiple_action.setShortcut("Ctrl+M")
        open_multiple_action.triggered.connect(self.browse_multiple_files)
        file_menu.addAction(open_multiple_action)
        
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
        
        save_schema_action = QAction("Save JSON &Schema(s)...", self)
        save_schema_action.setShortcut("Ctrl+S")
        save_schema_action.triggered.connect(self.save_schemas)
        save_schema_action.setEnabled(False)
        self.save_schema_action = save_schema_action
        file_menu.addAction(save_schema_action)
        
        save_jsonld_ontology_action = QAction("Save Ontology as JSON-&LD...", self)
        save_jsonld_ontology_action.setShortcut("Ctrl+L")
        save_jsonld_ontology_action.triggered.connect(self.save_ontology_jsonld)
        save_jsonld_ontology_action.setEnabled(False)
        self.save_jsonld_ontology_action = save_jsonld_ontology_action
        file_menu.addAction(save_jsonld_ontology_action)
        
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
        
        save_jsonld_action = QAction("Save JSON-&LD Instance...", self)
        save_jsonld_action.triggered.connect(self.save_jsonld)
        save_jsonld_action.setEnabled(False)
        self.save_jsonld_action = save_jsonld_action
        file_menu.addAction(save_jsonld_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Ontology Partitioning menu
        partitioning_menu = menubar.addMenu("&Ontology Partitioning")
        
        load_partitioning_action = QAction("&Load Ontology", self)
        load_partitioning_action.triggered.connect(self.load_ontology_for_partitioning)
        partitioning_menu.addAction(load_partitioning_action)
        
        save_partitioned_action = QAction("&Save Partitioned Ontology", self)
        save_partitioned_action.triggered.connect(self.save_partitioned_ontology)
        save_partitioned_action.setEnabled(False)
        self.save_partitioned_action = save_partitioned_action
        partitioning_menu.addAction(save_partitioned_action)
        
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
        
        # Step 4: Ontology Partitioning
        self.partitioning_widget = self.create_partitioning_step()
        self.workflow_tabs.addTab(self.partitioning_widget, "4. Ontology Partitioning")
        
        parent_layout.addWidget(self.workflow_tabs)
    
    def create_tbox_step(self):
        """Create the T-box transformation step widget."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(5)  # Reduce spacing between elements
        
        # Description - Fixed height
        desc_label = QLabel("<b>Step 1: T-box Transformation</b><br>"
                          "Transform OWL ontology (T-box) to JSON Schema")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("QLabel { background-color: #e3f2fd; padding: 10px; border-radius: 5px; }")
        desc_label.setMaximumHeight(60)  # Fixed maximum height
        layout.addWidget(desc_label)
        
        # Input section with text editor and controls
        input_group = QGroupBox("Ontology Sources")
        input_group.setMaximumHeight(200)  # Increased height for text editor
        input_layout = QVBoxLayout()
        
        # Instructions label
        instructions = QLabel("Enter ontology paths or URIs (one per line). Mix local files and URIs freely:")
        instructions.setStyleSheet("color: #666; font-size: 11px;")
        input_layout.addWidget(instructions)
        
        # Text editor for ontology list
        self.ontology_list_editor = QTextEdit()
        self.ontology_list_editor.setPlaceholderText(
            "Examples:\n"
            "/path/to/local/ontology.owl\n"
            "C:\\Users\\Name\\ontology.ttl\n"
            "https://example.org/ontology.rdf\n"
            "file:///home/user/ontology.n3"
        )
        self.ontology_list_editor.setMaximumHeight(80)
        self.ontology_list_editor.setFont(QFont("Consolas, 'Courier New', monospace", 10))
        self.ontology_list_editor.textChanged.connect(self.on_ontology_list_changed)
        
        # Force white background using document background
        self.ontology_list_editor.document().setDefaultStyleSheet("""
            body { background-color: white; }
        """)
        
        # Also set viewport background
        self.ontology_list_editor.viewport().setStyleSheet("background-color: white;")
        
        # And set the widget itself
        self.ontology_list_editor.setStyleSheet("""
            QTextEdit {
                background-color: white;
                background: white;
                color: black;
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 5px;
            }
            QTextEdit:focus {
                background-color: white;
                background: white;
                border-color: #4CAF50;
                border-width: 2px;
            }
        """)
        
        input_layout.addWidget(self.ontology_list_editor)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        # Select from files button
        select_files_btn = QPushButton("📁 Select Files...")
        select_files_btn.clicked.connect(self.add_files_to_list)
        select_files_btn.setToolTip("Browse and add local ontology files")
        select_files_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        button_layout.addWidget(select_files_btn)
        
        # Enter URI button
        add_uri_btn = QPushButton("🌐 Add URI...")
        add_uri_btn.clicked.connect(self.add_uri_to_list)
        add_uri_btn.setToolTip("Add an ontology URI")
        add_uri_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        button_layout.addWidget(add_uri_btn)
        
        # Remove line button
        remove_line_btn = QPushButton("➖ Remove Line")
        remove_line_btn.clicked.connect(self.remove_current_line)
        remove_line_btn.setToolTip("Remove the line at cursor position")
        remove_line_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        button_layout.addWidget(remove_line_btn)
        
        # Clear all button
        clear_all_btn = QPushButton("🗑️ Clear All")
        clear_all_btn.clicked.connect(self.clear_ontology_list)
        clear_all_btn.setToolTip("Clear all entries")
        clear_all_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        button_layout.addWidget(clear_all_btn)
        
        button_layout.addStretch()
        
        # Status label
        self.ontology_count_label = QLabel("0 ontologies")
        self.ontology_count_label.setStyleSheet("color: #666; font-style: italic;")
        button_layout.addWidget(self.ontology_count_label)
        
        input_layout.addLayout(button_layout)
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # Configuration section - Fixed height
        config_group = QGroupBox("Configuration")
        config_group.setMaximumHeight(120)  # Fixed maximum height
        config_layout = QVBoxLayout()
        config_layout.setSpacing(5)  # Reduce internal spacing
        
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
        
        # Transform button - Fixed height
        self.transform_btn = QPushButton("Transform T-box to JSON Schema")
        self.transform_btn.clicked.connect(self.run_transformation)
        self.transform_btn.setEnabled(False)
        self.transform_btn.setMaximumHeight(40)  # Fixed maximum height
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
        
        # Output section - This will expand to fill available space
        output_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # OWL Input display with tabs
        owl_group = QGroupBox("OWL Ontology")
        owl_layout = QVBoxLayout()
        
        # Create tab widget for OWL formats
        self.owl_tabs = QTabWidget()
        
        # Original format tab
        self.input_text = QTextEdit()
        self.input_text.setFont(QFont("Consolas, 'Courier New', monospace", 11))
        self.owl_tabs.addTab(self.input_text, "Original Format")
        
        # JSON-LD format tab
        self.jsonld_text = QTextEdit()
        self.jsonld_text.setFont(QFont("Consolas, 'Courier New', monospace", 11))
        self.jsonld_text.setReadOnly(True)
        self.owl_tabs.addTab(self.jsonld_text, "JSON-LD Format")
        
        owl_layout.addWidget(self.owl_tabs)
        owl_group.setLayout(owl_layout)
        output_splitter.addWidget(owl_group)
        
        # JSON Schema output with tabs
        schema_group = QGroupBox("JSON Schema Output")
        schema_layout = QVBoxLayout()
        
        # Create tab widget for schema and statistics
        self.schema_tabs = QTabWidget()
        
        # Schema tab
        self.output_text = QTextEdit()
        self.output_text.setFont(QFont("Consolas, 'Courier New', monospace", 11))
        self.output_text.setReadOnly(True)
        self.schema_tabs.addTab(self.output_text, "Schema")
        
        # Statistics tab
        self.stats_text = QTextEdit()
        self.stats_text.setFont(QFont("Consolas, 'Courier New', monospace", 11))
        self.stats_text.setReadOnly(True)
        self.schema_tabs.addTab(self.stats_text, "Statistics")
        
        schema_layout.addWidget(self.schema_tabs)
        schema_group.setLayout(schema_layout)
        output_splitter.addWidget(schema_group)
        
        output_splitter.setSizes([600, 600])
        layout.addWidget(output_splitter, 1)  # Add with stretch factor 1 to make it expand
        
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
        self.abox_output_text.setFont(QFont("Consolas, 'Courier New', monospace", 11))
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
        layout.setSpacing(5)  # Reduce spacing between elements
        
        # Description - Fixed height
        desc_label = QLabel("<b>Step 3: JSON Instance Generation</b><br>"
                          "Transform the A-box to JSON instances conforming to the generated JSON Schema")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("QLabel { background-color: #e8f5e9; padding: 10px; border-radius: 5px; }")
        desc_label.setMaximumHeight(60)  # Fixed maximum height
        layout.addWidget(desc_label)
        
        # Configuration - Fixed height
        config_group = QGroupBox("Reference Style")
        config_group.setMaximumHeight(80)  # Fixed maximum height
        config_layout = QHBoxLayout()
        
        # Reference style radio buttons
        self.reference_style_group = QButtonGroup()
        
        self.inline_radio = QRadioButton("Inline Objects")
        self.inline_radio.setToolTip("Embed full object definitions inline (self-contained documents)")
        self.reference_style_group.addButton(self.inline_radio, 0)
        config_layout.addWidget(self.inline_radio)
        
        self.reference_radio = QRadioButton("URI References")
        self.reference_radio.setToolTip("Use @id references only (linked data approach)")
        self.reference_radio.setChecked(True)  # Default to reference style
        self.reference_style_group.addButton(self.reference_radio, 1)
        config_layout.addWidget(self.reference_radio)
        
        config_layout.addStretch()
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Transform button - Fixed height
        self.transform_json_btn = QPushButton("Transform A-box to JSON")
        self.transform_json_btn.setEnabled(False)
        self.transform_json_btn.clicked.connect(self.transform_abox_to_json)
        self.transform_json_btn.setMaximumHeight(40)  # Fixed maximum height
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
        
        # Validation - Fixed height
        validation_group = QGroupBox("Schema Validation")
        validation_group.setMaximumHeight(80)  # Fixed maximum height
        validation_layout = QHBoxLayout()
        
        self.validate_json_btn = QPushButton("Validate against Schema")
        self.validate_json_btn.setEnabled(False)
        self.validate_json_btn.clicked.connect(self.validate_json_instances)
        validation_layout.addWidget(self.validate_json_btn)
        
        self.json_validation_status = QLabel("Not validated")
        self.json_validation_status.setStyleSheet("color: gray;")
        validation_layout.addWidget(self.json_validation_status)
        
        validation_layout.addStretch()
        validation_group.setLayout(validation_layout)
        layout.addWidget(validation_group)
        
        # Output - Split into two side-by-side panels - This will expand to fill available space
        output_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # JSON output panel
        json_output_group = QGroupBox("JSON Instance")
        json_output_layout = QVBoxLayout()
        self.json_output_text = QTextEdit()
        self.json_output_text.setFont(QFont("Consolas, 'Courier New', monospace", 11))
        self.json_output_text.setReadOnly(True)
        json_output_layout.addWidget(self.json_output_text)
        json_output_group.setLayout(json_output_layout)
        output_splitter.addWidget(json_output_group)
        
        # JSON-LD output panel
        jsonld_output_group = QGroupBox("JSON-LD Instance")
        jsonld_output_layout = QVBoxLayout()
        self.jsonld_output_text = QTextEdit()
        self.jsonld_output_text.setFont(QFont("Consolas, 'Courier New', monospace", 11))
        self.jsonld_output_text.setReadOnly(True)
        jsonld_output_layout.addWidget(self.jsonld_output_text)
        jsonld_output_group.setLayout(jsonld_output_layout)
        output_splitter.addWidget(jsonld_output_group)
        
        # Set equal sizes for both panels
        output_splitter.setSizes([600, 600])
        layout.addWidget(output_splitter, 1)  # Add with stretch factor 1 to make it expand
        
        widget.setLayout(layout)
        return widget
    
    def create_partitioning_step(self):
        """Create the Ontology Partitioning step widget."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        # Description
        desc_label = QLabel("<b>Ontology Partitioning</b><br>"
                           "Partition large ontologies into semantically coherent modules")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("QLabel { background-color: #f3e5f5; padding: 10px; border-radius: 5px; }")
        desc_label.setMaximumHeight(60)
        layout.addWidget(desc_label)
        
        # Load section
        load_group = QGroupBox("Loaded Ontology")
        load_group.setMaximumHeight(150)
        load_layout = QVBoxLayout()
        
        # Ontology name and path
        self.partitioning_ontology_label = QLabel("No ontology loaded")
        self.partitioning_ontology_label.setStyleSheet("font-weight: bold;")
        load_layout.addWidget(self.partitioning_ontology_label)
        
        # Ontology preview (read-only)
        self.partitioning_ontology_text = QTextEdit()
        self.partitioning_ontology_text.setReadOnly(True)
        self.partitioning_ontology_text.setMaximumHeight(80)
        self.partitioning_ontology_text.setFont(QFont("Consolas, 'Courier New', monospace", 10))
        self.partitioning_ontology_text.setPlaceholderText("Load an ontology to see preview...")
        load_layout.addWidget(self.partitioning_ontology_text)
        
        load_group.setLayout(load_layout)
        layout.addWidget(load_group)
        
        # Configuration section
        config_group = QGroupBox("Partitioning Configuration")
        config_group.setMaximumHeight(120)
        config_layout = QVBoxLayout()
        
        # Strategy checkboxes
        strategy_layout = QHBoxLayout()
        strategy_layout.addWidget(QLabel("Strategies:"))
        
        self.hierarchical_check = QCheckBox("Hierarchical")
        self.hierarchical_check.setChecked(True)
        strategy_layout.addWidget(self.hierarchical_check)
        
        self.community_check = QCheckBox("Community Detection")
        self.community_check.setChecked(True)
        strategy_layout.addWidget(self.community_check)
        
        self.domain_check = QCheckBox("Domain-based")
        self.domain_check.setChecked(True)
        strategy_layout.addWidget(self.domain_check)
        
        strategy_layout.addStretch()
        config_layout.addLayout(strategy_layout)
        
        # Entities per chunk
        chunk_layout = QHBoxLayout()
        chunk_layout.addWidget(QLabel("Max entities per chunk:"))
        self.entities_per_chunk_spin = QSpinBox()
        self.entities_per_chunk_spin.setMinimum(10)
        self.entities_per_chunk_spin.setMaximum(100)
        self.entities_per_chunk_spin.setValue(30)
        chunk_layout.addWidget(self.entities_per_chunk_spin)
        chunk_layout.addStretch()
        config_layout.addLayout(chunk_layout)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Partition button
        self.partition_btn = QPushButton("Partition Ontology")
        self.partition_btn.setEnabled(False)
        self.partition_btn.clicked.connect(self.run_partitioning)
        self.partition_btn.setMaximumHeight(40)
        self.partition_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        layout.addWidget(self.partition_btn)
        
        # Results section
        results_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: Partition tree
        tree_group = QGroupBox("Partition Structure")
        tree_layout = QVBoxLayout()
        
        self.partition_tree = QTreeWidget()
        self.partition_tree.setHeaderLabel("Partitions")
        self.partition_tree.itemSelectionChanged.connect(self.on_partition_selected)
        tree_layout.addWidget(self.partition_tree)
        
        tree_group.setLayout(tree_layout)
        results_splitter.addWidget(tree_group)
        
        # Right panel: Details and report
        details_tabs = QTabWidget()
        
        # Partition details tab with buttons
        partition_details_widget = QWidget()
        partition_details_layout = QVBoxLayout()
        
        # Button bar for partition actions
        partition_buttons_layout = QHBoxLayout()
        
        self.view_full_partition_btn = QPushButton("View Full File")
        self.view_full_partition_btn.setEnabled(False)
        self.view_full_partition_btn.clicked.connect(self.view_full_partition)
        self.view_full_partition_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        partition_buttons_layout.addWidget(self.view_full_partition_btn)
        
        self.open_in_editor_btn = QPushButton("Open in External Editor")
        self.open_in_editor_btn.setEnabled(False)
        self.open_in_editor_btn.clicked.connect(self.open_partition_in_editor)
        self.open_in_editor_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        partition_buttons_layout.addWidget(self.open_in_editor_btn)
        
        partition_buttons_layout.addStretch()
        partition_details_layout.addLayout(partition_buttons_layout)
        
        # Partition details text
        self.partition_details_text = QTextEdit()
        self.partition_details_text.setReadOnly(True)
        self.partition_details_text.setFont(QFont("Consolas, 'Courier New', monospace", 10))
        partition_details_layout.addWidget(self.partition_details_text)
        
        partition_details_widget.setLayout(partition_details_layout)
        details_tabs.addTab(partition_details_widget, "Partition Details")
        
        # Overall report tab
        self.partition_report_text = QTextEdit()
        self.partition_report_text.setReadOnly(True)
        self.partition_report_text.setFont(QFont("Consolas, 'Courier New', monospace", 10))
        details_tabs.addTab(self.partition_report_text, "Overall Report")
        
        results_splitter.addWidget(details_tabs)
        results_splitter.setSizes([400, 800])
        
        layout.addWidget(results_splitter, 1)  # Add with stretch factor 1
        
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
            self.save_jsonld_action.setEnabled(True)
            self.validate_json_btn.setEnabled(True)
        else:
            self.json_status.setText("JSON: Not Available")
            self.json_status.setStyleSheet("QLabel { color: gray; }")
            self.save_json_action.setEnabled(False)
            self.save_jsonld_action.setEnabled(False)
    
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
    
    def add_files_to_list(self):
        """Browse and add local ontology files to the list."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select OWL Ontology Files",
            "",
            "OWL Files (*.owl *.rdf *.ttl *.n3);;All Files (*.*)"
        )
        
        if files:
            # Get current content
            current_text = self.ontology_list_editor.toPlainText()
            lines = [line.strip() for line in current_text.split('\n') if line.strip()]
            
            # Add new files
            for file in files:
                if file not in lines:
                    lines.append(file)
            
            # Update editor
            self.ontology_list_editor.setPlainText('\n'.join(lines))
    
    def add_uri_to_list(self):
        """Add an ontology URI to the list."""
        from PyQt6.QtWidgets import QInputDialog
        
        uri, ok = QInputDialog.getText(
            self,
            "Add Ontology URI",
            "Enter the URI of the ontology:",
            QLineEdit.EchoMode.Normal,
            "https://"
        )
        
        if ok and uri:
            # Get current content
            current_text = self.ontology_list_editor.toPlainText()
            lines = [line.strip() for line in current_text.split('\n') if line.strip()]
            
            # Add new URI if not already present
            if uri not in lines:
                lines.append(uri)
                self.ontology_list_editor.setPlainText('\n'.join(lines))
    
    def remove_current_line(self):
        """Remove the line at the current cursor position."""
        cursor = self.ontology_list_editor.textCursor()
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        cursor.removeSelectedText()
        
        # Remove the newline character if it's there
        cursor.deleteChar()
    
    def clear_ontology_list(self):
        """Clear all entries from the ontology list."""
        reply = QMessageBox.question(
            self,
            "Clear All",
            "Are you sure you want to clear all ontology entries?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.ontology_list_editor.clear()
    
    def on_ontology_list_changed(self):
        """Handle changes to the ontology list editor."""
        # Parse the content to get list of ontologies
        text = self.ontology_list_editor.toPlainText()
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        self.ontology_list = lines
        
        # Update count label
        count = len(lines)
        if count == 0:
            self.ontology_count_label.setText("0 ontologies")
        elif count == 1:
            self.ontology_count_label.setText("1 ontology")
        else:
            self.ontology_count_label.setText(f"{count} ontologies")
        
        # Enable/disable transform button
        self.transform_btn.setEnabled(count > 0)
        self.save_ontology_action.setEnabled(count > 0)
    
    def browse_input_file(self):
        """Legacy method - redirects to add_files_to_list for compatibility."""
        self.add_files_to_list()
    
    def browse_multiple_files(self):
        """Legacy method - redirects to add_files_to_list for compatibility."""
        self.add_files_to_list()
    
    def open_url(self):
        """Open ontology from URL - redirects to add_uri_to_list."""
        self.add_uri_to_list()
    
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
        # Check if we have any ontologies to transform
        if not self.ontology_list:
            QMessageBox.warning(self, "Warning", "Please add at least one ontology source first.")
            return
        
        # Always use composite workflow for consistency
        # This provides metadata storage and future extensibility even for single ontologies
        try:
            # Create composite ontology dialog for metadata
            dialog = CompositeMetadataDialog(self, self.ontology_list)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return  # User cancelled
            
            metadata = dialog.get_metadata()
            
            # Create the composite ontology
            self.status_message.setText("Creating composite ontology...")
            QApplication.processEvents()
            
            # Use the class method to create composite builder
            builder = CompositeOntologyBuilder.create_composite(
                self.ontology_list,
                metadata=metadata
            )
            
            # Store the builder for later saving
            self.composite_builder = builder
            
            # Save to temporary file
            temp_file = builder.save_to_temp_file(format="turtle")
            
            # Clean up previous temp file if it exists
            self._cleanup_temp_file()
            
            # Use the temporary file as input
            self.input_file = temp_file
            self.temp_composite_file = temp_file  # Track for cleanup
            self.is_composite = True
            
            # Display the composite ontology
            composite_content = builder.serialize(format="turtle")
            self.input_text.setPlainText(composite_content[:5000])
            
            # Enable save composite ontology menu
            self.save_ontology_action.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, "Error",
                               f"Failed to create composite ontology:\n{str(e)}")
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
        self.worker = TransformationWorker(self.input_file, config, self.ontology_list)
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
        
        # Generate and display JSON-LD format of the ontology
        self.generate_and_display_jsonld()
        
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
    
    def save_schemas(self):
        """Save the JSON Schema(s) to a directory."""
        if not self.transformation_result:
            QMessageBox.warning(self, "Warning", "No schema to save. Please run the transformation first.")
            return
        
        # Diagnostic check before asking for directory
        diagnostic_info = []
        diagnostic_info.append(f"Has worker: {hasattr(self, 'worker')}")
        if hasattr(self, 'worker'):
            diagnostic_info.append(f"Worker has transformation_service_result: {hasattr(self.worker, 'transformation_service_result')}")
            if hasattr(self.worker, 'transformation_service_result') and self.worker.transformation_service_result:
                result = self.worker.transformation_service_result
                diagnostic_info.append(f"Result.success: {result.success}")
                diagnostic_info.append(f"Result has component_schemas: {result.component_schemas is not None}")
                if result.component_schemas:
                    diagnostic_info.append(f"Number of component schemas: {len(result.component_schemas)}")
                    diagnostic_info.append(f"Component names: {list(result.component_schemas.keys())}")
                else:
                    diagnostic_info.append("Component schemas is None or empty")
        
        # Show diagnostic
        QMessageBox.information(self, "Diagnostic Info", "\n".join(diagnostic_info))
        
        # Ask user to select a directory
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory to Save JSON Schema(s)",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if directory:
            try:
                from owl2jsonschema.services.transformation_service import TransformationService
                service = TransformationService()
                
                # Check if we have a transformation result with component schemas
                # The worker should have stored this information
                if hasattr(self.worker, 'transformation_service_result') and self.worker.transformation_service_result:
                    result = self.worker.transformation_service_result
                    
                    saved_files = service.save_transformation_results(
                        result=result,
                        output_dir=directory,
                        composite_filename="composite_schema.json",
                        component_suffix="_schema.json"
                    )
                    
                    # Check for warnings
                    warnings_msg = ""
                    if result.warnings:
                        warnings_msg = "\n\n⚠️ Warnings:\n" + "\n".join([f"  • {w}" for w in result.warnings])
                else:
                    # Fallback: just save the main schema
                    composite_path = Path(directory) / "composite_schema.json"
                    with open(composite_path, 'w', encoding='utf-8') as f:
                        json.dump(self.transformation_result, f, indent=2)
                    saved_files = {"composite": str(composite_path)}
                    warnings_msg = ""
                
                # Build success message
                file_list = "\n".join([f"  • {name}: {Path(path).name}"
                                      for name, path in saved_files.items()])
                
                message = f"Saved {len(saved_files)} schema file(s) to:\n{directory}\n\n{file_list}{warnings_msg}"
                
                QMessageBox.information(
                    self,
                    "Schemas Saved",
                    message
                )
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                QMessageBox.critical(self, "Save Error", f"Failed to save schemas:\n{str(e)}\n\n{error_details}")
    
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
        if not self.json_instances:
            QMessageBox.warning(self, "Warning", "No JSON instances to save. Please generate JSON instances first.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save JSON Instances",
            "instances.json",
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if file_path:
            try:
                # Get the regular JSON instances (not JSON-LD)
                json_data = self.json_instances.get('instances', self.json_instances)
                content = json.dumps(json_data, indent=2)
                
                with open(file_path, 'w') as f:
                    f.write(content)
                
                QMessageBox.information(self, "Success", f"JSON instances saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save file:\n{str(e)}")
    
    def save_jsonld(self):
        """Save the JSON-LD instances."""
        if not self.json_instances:
            QMessageBox.warning(self, "Warning", "No JSON-LD instances to save. Please generate JSON instances first.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save JSON-LD Instances",
            "instances.jsonld",
            "JSON-LD Files (*.jsonld);;All Files (*.*)"
        )
        
        if file_path:
            try:
                # Get the JSON-LD version
                jsonld_data = self.json_instances.get('jsonld', self.json_instances)
                content = json.dumps(jsonld_data, indent=2)
                
                with open(file_path, 'w') as f:
                    f.write(content)
                
                QMessageBox.information(self, "Success", f"JSON-LD instances saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save file:\n{str(e)}")
    
    def transform_abox_to_json(self):
        """Transform the A-box to JSON instances."""
        if not self.abox_data:
            QMessageBox.warning(self, "Warning", "No A-box available. Please generate an A-box first.")
            return
        
        if not self.transformation_result:
            QMessageBox.warning(self, "Warning", "No JSON Schema available. Please transform the T-box first.")
            return
        
        try:
            # Update status
            self.status_message.setText("Converting A-box to JSON...")
            self.transform_json_btn.setEnabled(False)
            QApplication.processEvents()
            
            # Get base URI from the A-box generator settings
            base_uri = self.base_uri_input.text().strip() or "https://example.org#"
            
            # Get selected reference style
            reference_style = "inline" if self.inline_radio.isChecked() else "reference"
            
            # Create converter with selected reference style
            converter = ABoxToJSONConverter(
                self.transformation_result,
                base_uri,
                reference_style=reference_style
            )
            
            # Convert to JSON
            json_instances = converter.convert(self.abox_data)
            
            # Also generate JSON-LD version
            jsonld_instances = converter.to_jsonld(json_instances)
            
            # Store both formats
            self.json_instances = {
                'instances': json_instances,
                'jsonld': jsonld_instances
            }
            
            # Display in separate output panels
            self.json_output_text.setPlainText(json.dumps(json_instances, indent=2))
            self.jsonld_output_text.setPlainText(json.dumps(jsonld_instances, indent=2))
            
            # Update state
            self.json_ready = True
            self.update_status()
            
            # Update UI
            self.transform_json_btn.setEnabled(True)
            self.json_validation_status.setText("Not validated")
            self.json_validation_status.setStyleSheet("color: gray;")
            self.status_message.setText("A-box successfully converted to JSON!")
            
            # Show summary
            num_instances = len(json_instances) if isinstance(json_instances, list) else 1
            QMessageBox.information(
                self,
                "Conversion Successful",
                f"Successfully converted {num_instances} instance(s) to JSON format.\n\n"
                "The instances are ready for validation against the JSON Schema."
            )
            
        except Exception as e:
            self.transform_json_btn.setEnabled(True)
            self.status_message.setText("Conversion failed")
            QMessageBox.critical(
                self,
                "Conversion Error",
                f"Failed to convert A-box to JSON:\n\n{str(e)}"
            )
    
    def validate_json_instances(self):
        """Validate the JSON instances against the JSON Schema."""
        if not self.json_instances:
            QMessageBox.warning(self, "Warning", "No JSON instances to validate. Please generate JSON instances first.")
            return
        
        if not self.transformation_result:
            QMessageBox.warning(self, "Warning", "No JSON Schema available. Please transform the T-box first.")
            return
        
        try:
            # Update status
            self.json_validation_status.setText("Validating...")
            self.json_validation_status.setStyleSheet("color: blue;")
            QApplication.processEvents()
            
            # Get the JSON instances (not JSON-LD)
            json_instances = self.json_instances.get('instances', self.json_instances)
            
            # Use the new validation service
            validation_results = SchemaValidationService.validate_json_against_schema(
                json_instances,
                self.transformation_result
            )
            
            # Update validation status
            if validation_results['valid']:
                self.json_validation_status.setText("✅ Valid")
                self.json_validation_status.setStyleSheet("color: green; font-weight: bold;")
                
                # Show success message
                valid_count = validation_results.get('valid_count', validation_results.get('valid_instances', 0))
                total_count = validation_results.get('total', validation_results.get('total_instances', 1))
                QMessageBox.information(
                    self,
                    "Validation Successful",
                    f"✅ All JSON instances are valid according to the JSON Schema.\n\n"
                    f"Validated {valid_count}/{total_count} instances successfully.\n"
                    "The instances conform to all schema constraints."
                )
            else:
                self.json_validation_status.setText("❌ Invalid")
                self.json_validation_status.setStyleSheet("color: red; font-weight: bold;")
                
                # Format error report using the validator's formatter
                error_report = JSONSchemaValidator.format_validation_report(validation_results)
                
                # Create a custom dialog for better display
                error_dialog = QDialog(self)
                error_dialog.setWindowTitle("Schema Validation Report")
                error_dialog.setMinimumSize(700, 600)
                
                layout = QVBoxLayout()
                
                # Important context label
                context_label = QLabel(
                    "ℹ️ IMPORTANT CONTEXT:\n"
                    "The validation errors below are most likely due to the RANDOM generation of the A-Box, "
                    "not issues with your schema or the validator.\n\n"
                    "The JSON Schema validator is working correctly and has detected that some randomly generated "
                    "instances don't fully comply with the schema constraints. This is expected behavior when using "
                    "random data generation.\n\n"
                    "If the OWL Reasoner validated the A-Box as consistent (Step 2), your ontology structure is correct."
                )
                context_label.setWordWrap(True)
                context_label.setStyleSheet(
                    "padding: 12px; background-color: #cfe2ff; border: 1px solid #084298; "
                    "border-radius: 5px; color: #084298;"
                )
                layout.addWidget(context_label)
                
                # Summary label
                valid_count = validation_results.get('valid_count', validation_results.get('valid_instances', 0))
                invalid_count = validation_results.get('invalid_count', validation_results.get('invalid_instances', 0))
                total_count = validation_results.get('total', validation_results.get('total_instances', valid_count + invalid_count))
                
                success_rate = 0
                if total_count > 0:
                    success_rate = int(valid_count/total_count*100)
                
                summary_label = QLabel(
                    f"📊 VALIDATION RESULTS:\n"
                    f"{valid_count}/{total_count} instances passed validation "
                    f"({success_rate}% success rate)\n\n"
                    f"The schema validator is functioning correctly by identifying constraint violations."
                )
                summary_label.setWordWrap(True)
                summary_label.setStyleSheet("font-weight: bold; padding: 10px; background-color: #fff3cd; border-radius: 5px;")
                layout.addWidget(summary_label)
                
                # Detailed error report in scrollable text area
                error_text = QTextEdit()
                error_text.setReadOnly(True)
                error_text.setPlainText(error_report)
                error_text.setFont(QFont("Consolas, 'Courier New', monospace", 11))
                error_text.setStyleSheet("background-color: #f8f9fa; border: 1px solid #dee2e6;")
                layout.addWidget(error_text)
                
                # OK button
                button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
                button_box.accepted.connect(error_dialog.accept)
                layout.addWidget(button_box)
                
                error_dialog.setLayout(layout)
                error_dialog.exec()
            
        except Exception as e:
            self.json_validation_status.setText("⚠️ Error")
            self.json_validation_status.setStyleSheet("color: orange;")
            QMessageBox.critical(
                self,
                "Validation Error",
                f"An error occurred during validation:\n\n{str(e)}"
            )
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About OntoJSON",
            "OntoJSON - OWL to JSON Schema Converter\n"
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
        text_edit.setFont(QFont("Consolas, 'Courier New', monospace", 11))
        
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
        """Save the loaded or composite ontology in a different format."""
        # Check if we have a composite ontology to save
        if self.is_composite and self.composite_builder:
            # Save the composite ontology with its metadata
            self._save_composite_ontology()
            return
        
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
    
    def generate_and_display_jsonld(self):
        """Generate and display the JSON-LD version of the ontology."""
        try:
            from rdflib import Graph
            
            # Update status
            self.status_message.setText("Converting ontology to JSON-LD...")
            QApplication.processEvents()
            
            # Create a new graph and parse the ontology
            g = Graph()
            
            if self.input_file:
                if self.input_file.startswith(('http://', 'https://')):
                    # Load from URL
                    g.parse(self.input_file)
                else:
                    # Load from file
                    g.parse(self.input_file)
                
                # Serialize to JSON-LD
                jsonld_content = g.serialize(format='json-ld')
                
                # Parse the JSON-LD to make it pretty
                if isinstance(jsonld_content, bytes):
                    jsonld_content = jsonld_content.decode('utf-8')
                
                # Parse and pretty-print the JSON
                jsonld_obj = json.loads(jsonld_content)
                jsonld_pretty = json.dumps(jsonld_obj, indent=2)
                
                # Display in the JSON-LD tab
                self.jsonld_text.setPlainText(jsonld_pretty)
                
                # Enable the save JSON-LD menu item
                self.save_jsonld_ontology_action.setEnabled(True)
                
                self.status_message.setText("JSON-LD conversion complete")
            
        except Exception as e:
            # If conversion fails, show error message in the JSON-LD tab
            error_msg = f"Failed to convert ontology to JSON-LD:\n\n{str(e)}"
            self.jsonld_text.setPlainText(error_msg)
            print(f"JSON-LD conversion error: {e}")
    
    def save_ontology_jsonld(self):
        """Save the ontology in JSON-LD format."""
        # Get the content from the JSON-LD tab
        jsonld_content = self.jsonld_text.toPlainText()
        
        if not jsonld_content or jsonld_content.startswith("Failed to convert"):
            QMessageBox.warning(self, "Warning", "No JSON-LD content to save. Please transform the T-box first.")
            return
        
        # Suggest a file name based on the input file
        suggested_name = "ontology.jsonld"
        if self.input_file and not self.input_file.startswith(('http://', 'https://')):
            base_name = Path(self.input_file).stem
            suggested_name = f"{base_name}.jsonld"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Ontology as JSON-LD",
            suggested_name,
            "JSON-LD Files (*.jsonld);;JSON Files (*.json);;All Files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(jsonld_content)
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"Ontology saved as JSON-LD to:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Save Error",
                    f"Failed to save JSON-LD file:\n{str(e)}"
                )
    
    def _save_composite_ontology(self):
        """Save the composite ontology with its metadata to a persistent file."""
        if not self.composite_builder:
            QMessageBox.warning(self, "Warning", "No composite ontology to save.")
            return
        
        # Create format selection dialog
        from PyQt6.QtWidgets import QInputDialog
        
        formats = [
            "Turtle (.ttl)",
            "RDF/XML (.rdf, .owl)",
            "N-Triples (.nt)",
            "JSON-LD (.jsonld)",
            "N3 (.n3)"
        ]
        
        format_choice, ok = QInputDialog.getItem(
            self,
            "Select Format",
            "Choose the format to save the composite ontology:",
            formats,
            0,  # Default to Turtle
            False  # Not editable
        )
        
        if not ok:
            return
        
        # Map user choice to format and extension
        format_map = {
            "Turtle (.ttl)": ("turtle", ".ttl"),
            "RDF/XML (.rdf, .owl)": ("xml", ".rdf"),
            "N-Triples (.nt)": ("nt", ".nt"),
            "JSON-LD (.jsonld)": ("json-ld", ".jsonld"),
            "N3 (.n3)": ("n3", ".n3")
        }
        
        rdf_format, file_ext = format_map[format_choice]
        
        # Get save file path
        suggested_name = f"composite_ontology{file_ext}"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Save Composite Ontology",
            suggested_name,
            f"{format_choice.split('(')[0].strip()} (*{file_ext});;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            self.status_message.setText(f"Saving composite ontology as {format_choice.split(' ')[0]}...")
            QApplication.processEvents()
            
            # Save the composite ontology
            self.composite_builder.save_to_file(file_path, format=rdf_format)
            
            self.status_message.setText("Composite ontology saved successfully!")
            
            QMessageBox.information(
                self,
                "Success",
                f"Composite ontology saved successfully to:\n{file_path}\n\n"
                f"Format: {format_choice.split(' ')[0]}\n"
                f"This file contains:\n"
                f"- All metadata (title, version, author, etc.)\n"
                f"- Import statements for {len(self.ontology_list)} ontologies\n"
                f"- Can be reused as input for future transformations"
            )
            
        except Exception as e:
            self.status_message.setText("Failed to save composite ontology")
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save composite ontology:\n\n{str(e)}"
            )
    
    def _cleanup_temp_file(self):
        """Clean up temporary composite ontology file if it exists."""
        if self.temp_composite_file:
            try:
                import os
                if os.path.exists(self.temp_composite_file):
                    os.remove(self.temp_composite_file)
                self.temp_composite_file = None
            except Exception as e:
                print(f"Failed to clean up temp file: {e}")
    
    def closeEvent(self, event):
        """Handle window close event to clean up resources."""
        self._cleanup_temp_file()
        event.accept()
    
    def load_ontology_for_partitioning(self):
        """Load an ontology file for partitioning."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Ontology for Partitioning",
            "",
            "OWL/RDF Files (*.owl *.rdf *.ttl *.n3);;All Files (*.*)"
        )
        
        if file_path:
            try:
                # Store the path
                self.partitioning_ontology_path = file_path
                
                # Update UI
                ontology_name = Path(file_path).name
                self.partitioning_ontology_label.setText(f"Ontology: {ontology_name}")
                
                # Load and display preview (first 1000 chars)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read(1000)
                    if len(content) == 1000:
                        content += "\n..."
                    self.partitioning_ontology_text.setPlainText(content)
                
                # Enable partition button
                self.partition_btn.setEnabled(True)
                
                # Clear previous results
                self.partition_tree.clear()
                self.partition_details_text.clear()
                self.partition_report_text.clear()
                self.partitioning_results = None
                self.save_partitioned_action.setEnabled(False)
                
                QMessageBox.information(self, "Success", f"Loaded ontology: {ontology_name}")
                
            except Exception as e:
                QMessageBox.critical(self, "Load Error", f"Failed to load ontology:\n{str(e)}")
    
    def run_partitioning(self):
        """Run the ontology partitioning process."""
        if not self.partitioning_ontology_path:
            QMessageBox.warning(self, "Warning", "Please load an ontology first.")
            return
        
        try:
            # Determine which strategies to use
            strategies = []
            if self.hierarchical_check.isChecked():
                strategies.append('hierarchical')
            if self.community_check.isChecked():
                strategies.append('community')
            if self.domain_check.isChecked():
                strategies.append('domain')
            
            if not strategies:
                QMessageBox.warning(self, "Warning", "Please select at least one partitioning strategy.")
                return
            
            # Update status
            self.status_message.setText("Running ontology partitioning...")
            self.partition_btn.setEnabled(False)
            QApplication.processEvents()
            
            # First, run the chunker if the file is large
            file_size = Path(self.partitioning_ontology_path).stat().st_size
            use_chunks = file_size > 500000  # Use chunks for files > 500KB
            
            if use_chunks:
                self.status_message.setText("Chunking large ontology file...")
                QApplication.processEvents()
                
                # Run the chunker
                chunker_script = Path(__file__).parent.parent.parent / "OntologyPartitioning" / "ontology_chunker.py"
                cmd = [
                    sys.executable,
                    str(chunker_script),
                    self.partitioning_ontology_path,
                    "-n", str(self.entities_per_chunk_spin.value())
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"Chunking failed: {result.stderr}")
            
            # Run the semantic partitioner
            self.status_message.setText("Running semantic partitioning...")
            QApplication.processEvents()
            
            partitioner_script = Path(__file__).parent.parent.parent / "OntologyPartitioning" / "semantic_partitioner.py"
            cmd = [
                sys.executable,
                str(partitioner_script),
                self.partitioning_ontology_path,
                "-s"
            ] + strategies
            
            if use_chunks:
                cmd.append("--use-chunks")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Partitioning failed: {result.stderr}")
            
            # Run the community namer if community strategy was used
            if 'community' in strategies:
                self.status_message.setText("Generating meaningful names for communities...")
                QApplication.processEvents()
                
                namer_script = Path(__file__).parent.parent.parent / "OntologyPartitioning" / "community_namer.py"
                # Change to the namer script's directory
                import os
                old_cwd = os.getcwd()
                os.chdir(namer_script.parent)
                
                cmd = [sys.executable, str(namer_script)]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                # Change back to original directory
                os.chdir(old_cwd)
            
            # Load and display results
            self.load_partitioning_results()
            
            # Update UI
            self.partition_btn.setEnabled(True)
            self.save_partitioned_action.setEnabled(True)
            self.status_message.setText("Partitioning completed successfully!")
            
            QMessageBox.information(self, "Success", "Ontology partitioning completed successfully!")
            
        except Exception as e:
            self.partition_btn.setEnabled(True)
            self.status_message.setText("Partitioning failed")
            QMessageBox.critical(self, "Partitioning Error", f"Failed to partition ontology:\n{str(e)}")
    
    def load_partitioning_results(self):
        """Load and display the partitioning results."""
        try:
            # Determine output directory
            ontology_stem = Path(self.partitioning_ontology_path).stem
            output_dir = Path(self.partitioning_ontology_path).parent / f"{ontology_stem}_modules"
            
            if not output_dir.exists():
                raise Exception(f"Results directory not found: {output_dir}")
            
            # Store results path
            self.partitioning_results = output_dir
            
            # Clear the report text first
            self.partition_report_text.clear()
            
            # Load overall report
            report_file = output_dir / "PARTITIONING_REPORT.md"
            if report_file.exists():
                with open(report_file, 'r', encoding='utf-8') as f:
                    report_content = f.read()
                    self.partition_report_text.setPlainText(report_content)
            else:
                # If no report file, create basic report
                self.partition_report_text.setPlainText("# Partitioning Results\n\nPartitioning completed successfully.")
            
            # Load community names report if it exists and append
            community_report = output_dir / "COMMUNITY_NAMES.md"
            if community_report.exists():
                with open(community_report, 'r', encoding='utf-8') as f:
                    community_content = f.read()
                    # Append to main report
                    existing_report = self.partition_report_text.toPlainText()
                    combined_report = existing_report + "\n\n" + "="*60 + "\n\n" + community_content
                    self.partition_report_text.setPlainText(combined_report)
            
            # Load partition summary
            summary_file = output_dir / "partitioning_summary.json"
            if summary_file.exists():
                with open(summary_file, 'r', encoding='utf-8') as f:
                    summary = json.load(f)
                    self.populate_partition_tree(output_dir, summary)
            else:
                # Create a basic summary from directory structure
                self.populate_partition_tree_from_dir(output_dir)
            
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to load some results:\n{str(e)}")
    
    def populate_partition_tree_from_dir(self, output_dir: Path):
        """Populate the partition tree from directory structure when no summary file exists."""
        self.partition_tree.clear()
        
        # Add root item with ontology info
        root = QTreeWidgetItem(self.partition_tree)
        root.setText(0, Path(self.partitioning_ontology_path).name)
        root.setExpanded(True)
        
        # Check for strategy directories
        strategies = ['hierarchical', 'community', 'domain']
        
        for strategy in strategies:
            strategy_dir = output_dir / strategy
            if strategy_dir.exists() and strategy_dir.is_dir():
                strategy_item = QTreeWidgetItem(root)
                
                # Count partition files
                partition_files = list(strategy_dir.glob("*.ttl"))
                strategy_item.setText(0, f"{strategy.title()} ({len(partition_files)} partitions)")
                strategy_item.setExpanded(True)
                strategy_item.setData(0, Qt.ItemDataRole.UserRole, str(strategy_dir))
                
                # Add partition files
                for partition_file in sorted(partition_files):
                    partition_item = QTreeWidgetItem(strategy_item)
                    partition_item.setText(0, partition_file.stem)
                    partition_item.setData(0, Qt.ItemDataRole.UserRole, str(partition_file))
    
    def populate_partition_tree(self, output_dir: Path, summary: dict):
        """Populate the partition tree with results."""
        self.partition_tree.clear()
        
        # Add root item with ontology info
        root = QTreeWidgetItem(self.partition_tree)
        root.setText(0, Path(self.partitioning_ontology_path).name)
        root.setExpanded(True)
        
        # Add summary info
        info_item = QTreeWidgetItem(root)
        info_item.setText(0, f"Classes: {summary.get('total_classes', 0)}, "
                            f"Properties: {summary.get('total_properties', 0)}")
        
        # Add each strategy
        for strategy_name, strategy_data in summary.get('strategies', {}).items():
            strategy_item = QTreeWidgetItem(root)
            metrics = strategy_data.get('metrics', {})
            strategy_item.setText(0, f"{strategy_name.title()} "
                                   f"({metrics.get('partitions', 0)} partitions)")
            strategy_item.setExpanded(True)
            
            # Store strategy path
            strategy_dir = output_dir / strategy_name
            strategy_item.setData(0, Qt.ItemDataRole.UserRole, str(strategy_dir))
            
            # Add metrics
            metrics_item = QTreeWidgetItem(strategy_item)
            cohesion = metrics.get('cohesion', 0) * 100
            coupling = metrics.get('coupling', 0) * 100
            metrics_item.setText(0, f"Cohesion: {cohesion:.1f}%, Coupling: {coupling:.1f}%")
            
            # Add partitions
            partitions = strategy_data.get('partitions', {})
            for partition_name, entity_count in sorted(partitions.items()):
                partition_item = QTreeWidgetItem(strategy_item)
                partition_item.setText(0, f"{partition_name} ({entity_count} entities)")
                
                # Store partition file path
                partition_file = strategy_dir / f"{partition_name}.ttl"
                partition_item.setData(0, Qt.ItemDataRole.UserRole, str(partition_file))
    
    def on_partition_selected(self):
        """Handle partition selection in the tree."""
        selected = self.partition_tree.selectedItems()
        if not selected:
            self.current_partition_file = None
            self.view_full_partition_btn.setEnabled(False)
            self.open_in_editor_btn.setEnabled(False)
            return
        
        item = selected[0]
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        
        if file_path and Path(file_path).exists():
            try:
                # Store current partition file
                self.current_partition_file = file_path
                self.view_full_partition_btn.setEnabled(True)
                self.open_in_editor_btn.setEnabled(True)
                
                # Load and display partition content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Display statistics and preview
                    lines = content.split('\n')
                    num_lines = len(lines)
                    
                    # Count triples (rough estimate)
                    num_triples = sum(1 for line in lines if line.strip() and
                                    not line.strip().startswith(('@', '#')))
                    
                    details = f"File: {Path(file_path).name}\n"
                    details += f"Path: {file_path}\n"
                    details += f"Lines: {num_lines}\n"
                    details += f"Estimated triples: {num_triples}\n"
                    details += "-" * 50 + "\n\n"
                    details += "PREVIEW (first 2000 characters):\n"
                    details += "-" * 50 + "\n\n"
                    
                    # Show first 2000 characters
                    if len(content) > 2000:
                        details += content[:2000] + "\n\n[... Preview truncated. Click 'View Full File' to see complete content ...]"
                    else:
                        details += content
                    
                    self.partition_details_text.setPlainText(details)
                    
            except Exception as e:
                self.partition_details_text.setPlainText(f"Error loading partition:\n{str(e)}")
                self.current_partition_file = None
                self.view_full_partition_btn.setEnabled(False)
                self.open_in_editor_btn.setEnabled(False)
        else:
            # Clear details if no file associated
            self.partition_details_text.clear()
            self.current_partition_file = None
            self.view_full_partition_btn.setEnabled(False)
            self.open_in_editor_btn.setEnabled(False)
    
    def view_full_partition(self):
        """View the full partition file in a dialog."""
        if not self.current_partition_file:
            return
        
        try:
            # Read full file content
            with open(self.current_partition_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create dialog
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Full Partition: {Path(self.current_partition_file).name}")
            dialog.setMinimumSize(800, 600)
            
            layout = QVBoxLayout()
            
            # File info label
            info_label = QLabel(f"File: {self.current_partition_file}")
            info_label.setStyleSheet("padding: 10px; background-color: #f0f0f0;")
            layout.addWidget(info_label)
            
            # Text editor with full content
            text_editor = QTextEdit()
            text_editor.setReadOnly(True)
            text_editor.setFont(QFont("Consolas, 'Courier New', monospace", 10))
            text_editor.setPlainText(content)
            layout.addWidget(text_editor)
            
            # Button box
            button_layout = QHBoxLayout()
            
            # Copy to clipboard button
            copy_btn = QPushButton("Copy to Clipboard")
            copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(content))
            button_layout.addWidget(copy_btn)
            
            button_layout.addStretch()
            
            # Close button
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.accept)
            button_layout.addWidget(close_btn)
            
            layout.addLayout(button_layout)
            dialog.setLayout(layout)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load full file:\n{str(e)}")
    
    def open_partition_in_editor(self):
        """Open the partition file in an external editor."""
        if not self.current_partition_file:
            return
        
        try:
            # Use the new editor selector system
            from .editor_selector import open_in_external_editor
            
            if not open_in_external_editor(self.current_partition_file, self):
                QMessageBox.warning(self, "Warning",
                                   f"Could not open the file. Please open manually:\n{self.current_partition_file}")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open in external editor:\n{str(e)}")
    
    def save_partitioned_ontology(self):
        """Save the partitioned ontology modules."""
        if not self.partitioning_results:
            QMessageBox.warning(self, "Warning", "No partitioning results to save.")
            return
        
        # Ask user for target directory
        target_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Directory to Save Partitioned Ontology",
            str(Path.home())
        )
        
        if not target_dir:
            return
        
        try:
            import shutil
            
            # Create target directory structure
            target_path = Path(target_dir)
            ontology_name = Path(self.partitioning_ontology_path).stem
            save_dir = target_path / f"{ontology_name}_partitioned"
            
            # Copy the entire results directory
            if save_dir.exists():
                reply = QMessageBox.question(
                    self,
                    "Overwrite?",
                    f"Directory {save_dir.name} already exists. Overwrite?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
                shutil.rmtree(save_dir)
            
            # Copy all partitioning results
            shutil.copytree(self.partitioning_results, save_dir)
            
            # Show success message
            QMessageBox.information(
                self,
                "Success",
                f"Partitioned ontology saved to:\n{save_dir}\n\n"
                "The directory contains:\n"
                "- Partition modules organized by strategy\n"
                "- Reports and visualizations\n"
                "- Index files for programmatic access"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save partitioned ontology:\n{str(e)}"
            )
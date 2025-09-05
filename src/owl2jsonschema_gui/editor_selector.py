"""
External Editor Selector - Detects and manages external editor preferences
"""

import json
import platform
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QListWidget, QPushButton, QCheckBox, QMessageBox,
    QGroupBox, QListWidgetItem
)
from PyQt6.QtCore import Qt


class EditorInfo:
    """Information about an external editor."""
    
    def __init__(self, name: str, command: str, icon: str = "", description: str = ""):
        self.name = name
        self.command = command
        self.icon = icon
        self.description = description
    
    def __repr__(self):
        return f"EditorInfo({self.name}, {self.command})"


class EditorDetector:
    """Detects available text editors on the system."""
    
    # Common editors to check for on different platforms
    COMMON_EDITORS = {
        "Darwin": [  # macOS
            EditorInfo("Zed", "zed", "⚡", "High-performance code editor"),
            EditorInfo("Visual Studio Code", "code", "💻", "Popular code editor by Microsoft"),
            EditorInfo("Sublime Text", "subl", "📝", "Sophisticated text editor"),
            EditorInfo("TextMate", "mate", "📄", "Powerful macOS text editor"),
            EditorInfo("BBEdit", "bbedit", "📋", "Professional HTML and text editor"),
            EditorInfo("Atom", "atom", "⚛️", "Hackable text editor"),
            EditorInfo("Nova", "nova", "✨", "Native macOS code editor"),
            EditorInfo("CotEditor", "cot", "🗒️", "Lightweight plain-text editor"),
            EditorInfo("TextEdit (default)", "open -t", "📃", "macOS default text editor"),
        ],
        "Windows": [
            EditorInfo("Visual Studio Code", "code", "💻", "Popular code editor by Microsoft"),
            EditorInfo("Notepad++", "notepad++", "📝", "Free source code editor"),
            EditorInfo("Sublime Text", "subl", "📝", "Sophisticated text editor"),
            EditorInfo("Atom", "atom", "⚛️", "Hackable text editor"),
            EditorInfo("Visual Studio", "devenv", "🏢", "Full IDE by Microsoft"),
            EditorInfo("Notepad", "notepad", "📃", "Windows default text editor"),
        ],
        "Linux": [
            EditorInfo("Zed", "zed", "⚡", "High-performance code editor"),
            EditorInfo("Visual Studio Code", "code", "💻", "Popular code editor by Microsoft"),
            EditorInfo("Sublime Text", "subl", "📝", "Sophisticated text editor"),
            EditorInfo("Atom", "atom", "⚛️", "Hackable text editor"),
            EditorInfo("Gedit", "gedit", "📄", "GNOME text editor"),
            EditorInfo("Kate", "kate", "📋", "KDE text editor"),
            EditorInfo("Vim", "vim", "⌨️", "Vi improved - terminal editor"),
            EditorInfo("Emacs", "emacs", "🐃", "Extensible text editor"),
            EditorInfo("Nano", "nano", "📟", "Simple terminal editor"),
            EditorInfo("XED", "xed", "✏️", "X-Apps text editor"),
            EditorInfo("Pluma", "pluma", "🖊️", "MATE text editor"),
        ]
    }
    
    @classmethod
    def detect_available_editors(cls) -> List[EditorInfo]:
        """Detect which editors are available on the current system."""
        system = platform.system()
        available = []
        
        # Get the list of potential editors for this platform
        potential_editors = cls.COMMON_EDITORS.get(system, cls.COMMON_EDITORS.get("Linux", []))
        
        for editor in potential_editors:
            if cls.is_editor_available(editor.command):
                available.append(editor)
        
        # Always add a file manager option
        if system == "Darwin":
            available.append(EditorInfo("Open with Default App", "open", "📂", "Use system default"))
        elif system == "Windows":
            available.append(EditorInfo("Open with Default App", "start", "📂", "Use system default"))
        else:
            available.append(EditorInfo("Open with Default App", "xdg-open", "📂", "Use system default"))
        
        return available
    
    @staticmethod
    def is_editor_available(command: str) -> bool:
        """Check if a command is available on the system."""
        try:
            # Handle commands with arguments (like "open -t")
            cmd_parts = command.split()
            base_command = cmd_parts[0]
            
            # Use 'which' on Unix-like systems, 'where' on Windows
            check_command = "where" if platform.system() == "Windows" else "which"
            result = subprocess.run(
                [check_command, base_command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return result.returncode == 0
        except:
            return False


class EditorPreferences:
    """Manages user preferences for external editors."""
    
    def __init__(self, config_file: Path = None):
        if config_file is None:
            config_dir = Path.home() / ".owl2jsonschema"
            config_dir.mkdir(exist_ok=True)
            self.config_file = config_dir / "editor_preferences.json"
        else:
            self.config_file = config_file
        
        self.preferences = self.load_preferences()
    
    def load_preferences(self) -> Dict:
        """Load preferences from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            "default_editor": None,
            "always_use_default": False,
            "recent_editors": []
        }
    
    def save_preferences(self):
        """Save preferences to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.preferences, f, indent=2)
        except Exception as e:
            print(f"Failed to save editor preferences: {e}")
    
    def get_default_editor(self) -> Optional[str]:
        """Get the default editor command."""
        return self.preferences.get("default_editor")
    
    def set_default_editor(self, command: str):
        """Set the default editor command."""
        self.preferences["default_editor"] = command
        # Add to recent if not already there
        if command not in self.preferences.get("recent_editors", []):
            self.preferences.setdefault("recent_editors", []).insert(0, command)
            # Keep only last 5 recent editors
            self.preferences["recent_editors"] = self.preferences["recent_editors"][:5]
        self.save_preferences()
    
    def get_always_use_default(self) -> bool:
        """Check if we should always use the default editor."""
        return self.preferences.get("always_use_default", False)
    
    def set_always_use_default(self, value: bool):
        """Set whether to always use the default editor."""
        self.preferences["always_use_default"] = value
        self.save_preferences()


class EditorSelectorDialog(QDialog):
    """Dialog for selecting an external editor."""
    
    def __init__(self, parent=None, preferences: EditorPreferences = None):
        super().__init__(parent)
        self.preferences = preferences or EditorPreferences()
        self.selected_editor = None
        self.available_editors = EditorDetector.detect_available_editors()
        
        self.setWindowTitle("Select External Editor")
        self.setMinimumSize(500, 400)
        
        self.init_ui()
        self.load_current_selection()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("Choose an external editor to open the file:")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(title_label)
        
        # Available editors list
        editors_group = QGroupBox("Available Editors")
        editors_layout = QVBoxLayout()
        
        self.editors_list = QListWidget()
        self.editors_list.itemDoubleClicked.connect(self.accept)
        
        # Populate the list
        for editor in self.available_editors:
            item = QListWidgetItem(f"{editor.icon} {editor.name}")
            item.setData(Qt.ItemDataRole.UserRole, editor)
            if editor.description:
                item.setToolTip(editor.description)
            self.editors_list.addItem(item)
        
        editors_layout.addWidget(self.editors_list)
        editors_group.setLayout(editors_layout)
        layout.addWidget(editors_group)
        
        # Options
        options_layout = QHBoxLayout()
        
        self.set_default_check = QCheckBox("Set as default editor")
        options_layout.addWidget(self.set_default_check)
        
        self.always_use_check = QCheckBox("Always use default (don't ask again)")
        options_layout.addWidget(self.always_use_check)
        
        layout.addLayout(options_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        open_btn = QPushButton("Open")
        open_btn.clicked.connect(self.accept)
        open_btn.setDefault(True)
        button_layout.addWidget(open_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_current_selection(self):
        """Load the current default selection if any."""
        default_editor = self.preferences.get_default_editor()
        if default_editor:
            # Find and select the default editor in the list
            for i in range(self.editors_list.count()):
                item = self.editors_list.item(i)
                editor = item.data(Qt.ItemDataRole.UserRole)
                if editor.command == default_editor:
                    self.editors_list.setCurrentItem(item)
                    break
        elif self.editors_list.count() > 0:
            # Select the first item by default
            self.editors_list.setCurrentRow(0)
        
        # Set checkbox states
        self.always_use_check.setChecked(self.preferences.get_always_use_default())
    
    def accept(self):
        """Accept the dialog and save preferences."""
        current_item = self.editors_list.currentItem()
        if current_item:
            editor = current_item.data(Qt.ItemDataRole.UserRole)
            self.selected_editor = editor
            
            # Save preferences if requested
            if self.set_default_check.isChecked():
                self.preferences.set_default_editor(editor.command)
            
            if self.always_use_check.isChecked():
                self.preferences.set_always_use_default(True)
                # Also set as default if "always use" is checked
                self.preferences.set_default_editor(editor.command)
            
        super().accept()


class ExternalEditorLauncher:
    """Manages launching files in external editors."""
    
    def __init__(self, preferences: EditorPreferences = None):
        self.preferences = preferences or EditorPreferences()
    
    def open_file(self, file_path: str, parent_widget=None) -> bool:
        """
        Open a file in an external editor.
        
        Returns True if successfully opened, False otherwise.
        """
        # Check if we should use default without asking
        if self.preferences.get_always_use_default():
            default_editor = self.preferences.get_default_editor()
            if default_editor:
                return self._launch_editor(default_editor, file_path)
        
        # Show selector dialog
        dialog = EditorSelectorDialog(parent_widget, self.preferences)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.selected_editor:
                return self._launch_editor(dialog.selected_editor.command, file_path)
        
        return False
    
    def _launch_editor(self, command: str, file_path: str) -> bool:
        """Launch the editor with the given command."""
        try:
            # Handle commands with arguments
            cmd_parts = command.split()
            cmd_parts.append(file_path)
            
            # Launch the editor
            if platform.system() == "Windows":
                subprocess.Popen(cmd_parts, shell=True)
            else:
                subprocess.Popen(cmd_parts)
            
            return True
        except Exception as e:
            print(f"Failed to launch editor: {e}")
            return False


# Quick access function for the main window
def open_in_external_editor(file_path: str, parent_widget=None) -> bool:
    """
    Convenience function to open a file in an external editor.
    """
    launcher = ExternalEditorLauncher()
    return launcher.open_file(file_path, parent_widget)
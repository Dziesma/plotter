from typing import Optional, List, Union
import ROOT
import os
from .logger import package_logger
from .styles import Style


class ProcessTemplate:
    def __init__(self, name: str, color: int, style: str, error_bars: bool, label: str):
        self.name = name
        self.color = color
        self.style = style
        self.error_bars = error_bars
        self.label = label if label is not None else name

class Process(ProcessTemplate):
    def __init__(self, 
                 name: str,
                 file_path: str,
                 tree_name: str,
                 color: Optional[int] = 1,
                 weight: Optional[str] = None,
                 style: Optional[str] = Style.STACKED,
                 error_bars: Optional[bool] = True,
                 label: Optional[str] = None):
        """
        Initialize a physics process.
        
        Args:
            name: Process name (e.g., 'ttbar', 'Wjets', etc.)
            file_path: Path to ROOT file
            tree_name: Path of the TTree in the ROOT file
            color: ROOT color code for plotting
            weight: Weight expression (overrides plotter weight if specified)
            style: Style of process (stacked, line, points)
            error_bars: Whether to draw error bars
            label: Label for the process (defaults to name if not set)
        """
        super().__init__(name, color, style, error_bars, label)
        self.logger = package_logger.get_logger(f"process.{name}")
        
        # Validate file path and tree name
        if not os.path.isfile(file_path):
            self.logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        
        self.file_path = os.path.expandvars(file_path)
        self.tree_name = tree_name
        self.weight = weight
        
        # Create RDataFrame
        self.df = None
        self.logger.info(f"Initialized process: {self.name} with file:tree: {self.file_path}:{self.tree_name}")

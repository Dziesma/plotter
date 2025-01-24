from typing import Optional, List, Union
import ROOT
import os
from .logger import package_logger
from .styles import ErrorBandStyle


class ProcessTemplate:
    def __init__(self, name: str, color: int, stack: bool, error_style: str):
        self.name = name
        self.color = color
        self.stack = stack
        self.error_style = error_style

class Process(ProcessTemplate):
    def __init__(self, 
                 name: str,
                 file_path: str,
                 tree_name: str,
                 color: Optional[int] = 1,
                 weight: Optional[str] = None,
                 stack: Optional[bool] = True,
                 error_style: Optional[str] = ErrorBandStyle.POINTS):
        """
        Initialize a physics process.
        
        Args:
            name: Process name (e.g., 'ttbar', 'Wjets', etc.)
            file_path: Path to ROOT file
            tree_name: Path of the TTree in the ROOT file
            color: ROOT color code for plotting
            weight: Weight expression (overrides plotter weight if specified)
            stack: Whether to include in stack (False for data/signal)
            error_style: Style of error band
        """
        super().__init__(name, color, stack, error_style)
        self.logger = package_logger.get_logger(f"process.{name}")
        
        # Validate file path and tree name
        if not os.path.isfile(file_path):
            self.logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        
        self.file_path = os.path.expandvars(file_path)
        self.tree_name = tree_name
        self.weight = weight
        
        # Create RDataFrame
        self.df = ROOT.RDataFrame(tree_name, self.file_path)
        self.logger.info(f"Initialized process: {self.name} with file:tree: {self.file_path}:{self.tree_name}")

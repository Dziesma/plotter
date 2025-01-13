from typing import Optional, List, Union
import ROOT
import os
from .logger import package_logger

class Process:
    def __init__(self, 
                 name: str,
                 file_path: str,
                 tree_name: str,
                 color: int,
                 scale: float = 1.0,
                 stack: bool = True):
        """
        Initialize a physics process.
        
        Args:
            name: Process name (e.g., 'ttbar', 'Wjets', etc.)
            file_path: Path to ROOT file
            tree_name: Path of the TTree in the ROOT file
            color: ROOT color code for plotting
            scale: Scale factor (e.g., luminosity * cross-section)
            stack: Whether to include in stack (False for data/signal)
        """
        self.logger = package_logger.get_logger(f"process.{name}")
        self.name = name
        self.file_path = os.path.expandvars(file_path)
        self.tree_name = tree_name
        self.color = color
        self.scale = scale
        self.stack = stack
        
        # Create RDataFrame
        self.df = ROOT.RDataFrame(tree_name, file_path)

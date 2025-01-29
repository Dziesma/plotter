from typing import Optional, List, Dict
from .process import Process
from .histogram import Histogram

class Region:
    def __init__(self,
                 name: str,
                 selection: str,
                 include_processes: Optional[List[str]] = None,
                 exclude_processes: Optional[List[str]] = None,
                 include_histograms: Optional[List[str]] = None,
                 exclude_histograms: Optional[List[str]] = None):
        """
        Initialize a region configuration.
        
        Args:
            name: Region identifier
            selection: Region selection cut
            include_processes: List of process names to include (if None, include all)
            exclude_processes: List of process names to exclude (if None, exclude none)
            include_histograms: List of histogram names to include (if None, include all)
            exclude_histograms: List of histogram names to exclude (if None, exclude none)
        """
        self.name = name
        self.selection = selection
        self.include_processes = include_processes
        self.exclude_processes = exclude_processes
        self.include_histograms = include_histograms
        self.exclude_histograms = exclude_histograms 
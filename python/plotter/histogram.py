from typing import Optional, Literal, Union, List, Tuple, Dict
import ROOT
from .process import Process

class RatioConfig:
    def __init__(self, 
                 numerator: Union[str, Literal["stack"]],
                 denominator: Union[str, Literal["stack"]],
                 y_label: str = "Ratio",
                 y_min: float = 0.5,
                 y_max: float = 1.5,
                 error_option: str = ""):
        """
        Configure ratio panel settings.
        
        Args:
            numerator: Name of numerator process or "stack" to use stack
            denominator: Name of denominator process or "stack" to use stack
            y_label: Y-axis label
            y_min: Y-axis minimum
            y_max: Y-axis maximum
            error_option: Error propagation option for TH1::Divide
                         "" (default) = standard error propagation
                         "B" = binomial errors
        """
        self.numerator = numerator
        self.denominator = denominator
        self.y_label = y_label
        self.y_min = y_min
        self.y_max = y_max
        self.error_option = error_option

class Histogram:
    def __init__(self,
                 name: str,
                 variable: str,
                 binning: Union[Tuple[int, float, float], Tuple[int, List[float]]],
                 x_label: str,
                 y_label: str = "Events",
                 y_min: Optional[float] = None,
                 log_y: bool = False,
                 ratio_config: Optional[RatioConfig] = None,
                 include_processes: Optional[List[str]] = None,
                 exclude_processes: Optional[List[str]] = None,
                 error_bars: bool = True):
        """
        Initialize a histogram configuration.
        
        Args:
            name: Histogram identifier
            variable: Branch name or arithmetic expression
            binning: Binning configuration (TH1 argument as a tuple)
            x_label: X-axis label
            y_label: Y-axis label
            y_min: Minimum y-axis value (optional)
            log_y: Use log scale for y-axis
            ratio_config: Ratio configuration
            include_processes: List of process names to include (if None, include all)
            exclude_processes: List of process names to exclude (if None, exclude none)
            error_bars: Draw error bars
        """
        self.name = name
        self.variable = variable
        self.binning = binning
        self.x_label = x_label
        self.y_label = y_label
        self.y_min = y_min
        self.log_y = log_y
        self.ratio_config = ratio_config
        self.include_processes = include_processes
        self.exclude_processes = exclude_processes
        self.error_bars = error_bars
        
        # Will store actual histograms
        self.histograms: List[Tuple[Process, ROOT.TH1F]] = []
        self.merged_histograms: Dict[str, ROOT.TH1F] = {}

from typing import Optional, List, Dict, Union
import ROOT
import os
from .process import Process
from .histogram import Histogram
from .logger import package_logger

class Plotter:
    def __init__(self, weight: str = "1"):
        """Initialize the plotter with ATLAS style settings."""
        # Suppress ROOT info messages
        ROOT.gROOT.SetBatch(True)  # Run in batch mode
        ROOT.gErrorIgnoreLevel = ROOT.kWarning  # Only show warnings and above

        # Set up processes and histograms
        self.processes: List[Process] = []
        self.histograms: List[Histogram] = []
        self.output_dir = "plots"
        self.weight = weight
        
        # Set ATLAS style
        self._set_atlas_style()
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.logger = package_logger.get_logger("plotter")
        self.logger.info("Plotter initialized")
    
    def add_process(self, process: Process) -> None:
        """Add a process to the plotter."""
        self.processes.append(process)
    
    def add_histogram(self, histogram: Histogram) -> None:
        """Add a histogram configuration to the plotter."""
        self.histograms.append(histogram)

    def run(self) -> None:
        """Process all histograms using RDataFrame."""
        actions = []
        
        # Loop over all histogram configurations
        for hist in self.histograms:
            # Determine which processes to include
            processes_to_use = []
            if hist.include_processes is not None:
                # Only include specified processes
                processes_to_use = [p for p in self.processes if p.name in hist.include_processes]
            elif hist.exclude_processes is not None:
                # Include all processes except those specifieds
                processes_to_use = [p for p in self.processes if p.name not in hist.exclude_processes]
            else:
                # Include all processes
                processes_to_use = self.processes
            
            # Loop over selected processes
            for proc in processes_to_use:
                # Create histogram model
                hist_name = f"{hist.name}_{proc.name}"
                h_model = ROOT.RDF.TH1DModel(
                    hist_name,
                    "",
                    hist.bins,
                    hist.x_min,
                    hist.x_max
                )
                
                # Apply selection if any
                df = proc.df
                if hist.selection:
                    df = df.Filter(hist.selection)
                
                # Use process-specific weight if specified, otherwise use plotter weight
                weight = proc.weight if proc.weight else self.weight
                
                # Add weight as a column to the dataframe
                df = df.Define("total_weight", weight)
                
                # Book histogram with weight column
                h = df.Histo1D(h_model, hist.variable, "total_weight")
                actions.append(h)
                
                # Store in histogram object
                hist.histograms[proc.name] = h
        
        # Process all actions in parallel
        ROOT.RDF.RunGraphs(actions)
        self.logger.info("Histograms processed")
        
        # Create plots
        self._make_plots()
        self.logger.info("All plots created")
    
    def _make_plots(self) -> None:
        """Create and save all plots."""
        for hist in self.histograms:
            # Create main pad and ratio pad if needed
            canvas_name = f"canvas_{hist.name}"
            canvas = ROOT.TCanvas(canvas_name, canvas_name, 800, 900)
            
            # Configure pads
            if hist.ratio_config:
                # Main pad for histogram
                upper_pad = ROOT.TPad(f"upper_pad_{hist.name}", f"upper_pad_{hist.name}", 0, 0.3, 1, 1)
                self._configure_pad_margins(upper_pad, is_upper=True)
                upper_pad.Draw()
                
                # Lower pad for ratio
                lower_pad = ROOT.TPad(f"lower_pad_{hist.name}", f"lower_pad_{hist.name}", 0, 0, 1, 0.3)
                self._configure_pad_margins(lower_pad, is_upper=False)
                lower_pad.Draw()

                if not lower_pad:
                    self.logger.error(f"Lower pad not created for histogram {hist.name}. Skipping plot.")
                    continue
                
                upper_pad.cd()
            else:
                canvas.SetRightMargin(0.12)  # Increased margin for single pad plots
                canvas.cd()

            # Create stack and legend
            stack = ROOT.THStack("stack", "")
            
            # Create legend with adjusted position and size
            legend = ROOT.TLegend(0.70, 0.70, 0.90, 0.90)
            legend.SetBorderSize(0)
            legend.SetFillStyle(0)
            
            # Separate stacked and unstacked processes
            stacked_hists = []
            unstacked_hists = []
            
            # Merge histograms from processes with same name
            merged_hists = self._merge_histograms(hist)
            
            # Process merged histograms
            processed_names = set()
            for proc in self.processes:
                if proc.name in processed_names:
                    continue
                    
                h = merged_hists[proc.name].Clone()
                h.SetLineColor(proc.color)
                h.SetLineWidth(2)
                
                if proc.stack:
                    h.SetFillColor(proc.color)
                    stacked_hists.append(h)
                    legend.AddEntry(h, proc.name, "f")
                else:
                    h.SetFillStyle(0)
                    unstacked_hists.append((h, h.Integral()))
                    legend.AddEntry(h, proc.name, "l")
                    
                processed_names.add(proc.name)
            
            # Sort unstacked histograms by integral (largest first)
            unstacked_hists.sort(key=lambda x: x[1], reverse=True)
            unstacked_hists = [h[0] for h in unstacked_hists]  # Extract just the histograms
            
            # Add to stack in reverse order (largest first)
            for h in reversed(stacked_hists):
                stack.Add(h)
            
            # Set log scale if configured
            if hist.ratio_config:
                upper_pad.cd()
                if hist.log_y:
                    upper_pad.SetLogy()
            else:
                canvas.cd()
                if hist.log_y:
                    canvas.SetLogy()

            # Handle drawing and axis setup
            if len(stacked_hists) > 0:
                stack.Draw("HIST")
                main_hist = stack
            else:
                unstacked_hists[0].Draw("HIST")
                main_hist = unstacked_hists[0]
                for h in unstacked_hists[1:]:
                    h.Draw("HIST SAME")
            
            # Configure axes
            self._configure_axes(hist, main_hist, bool(hist.ratio_config))

            # Set maximum and minimum to avoid legend overlap
            if hist.y_min is not None:
                main_hist.SetMinimum(hist.y_min)
            
            if len(stacked_hists) > 0:
                max_height = max(h.GetMaximum() for h in stacked_hists)
            else:
                max_height = max(h.GetMaximum() for h in unstacked_hists)
                
            if hist.log_y:
                main_hist.SetMaximum(max_height * 10)
            else:
                main_hist.SetMaximum(max_height * 1.4)
            
            # Draw legend
            legend.Draw()
            
            # Draw ATLAS label
            self._draw_atlas_label(has_ratio=bool(hist.ratio_config))
            
            # Handle ratio plot if configured
            if hist.ratio_config:
                lower_pad.cd()
                
                # Get numerator histogram
                if hist.ratio_config.numerator == "stack":
                    if not stacked_hists:
                        self.logger.error("Stack requested for ratio numerator but no stacked histograms found")
                        continue
                    h_num = stacked_hists[0].Clone()
                    for h in stacked_hists[1:]:
                        h_num.Add(h)
                else:
                    h_num = merged_hists[hist.ratio_config.numerator].Clone()
                
                # Get denominator histogram
                if hist.ratio_config.denominator == "stack":
                    if not stacked_hists:
                        self.logger.error("Stack requested for ratio denominator but no stacked histograms found")
                        continue
                    h_den = stacked_hists[0].Clone()
                    for h in stacked_hists[1:]:
                        h_den.Add(h)
                else:
                    h_den = merged_hists[hist.ratio_config.denominator].Clone()
                
                # Create ratio histogram
                h_ratio = h_num.Clone("ratio")
                h_ratio.Divide(h_num, h_den, 1.0, 1.0, hist.ratio_config.error_option)
                
                # Configure and draw ratio plot
                self._configure_ratio_plot(h_ratio, hist)
                h_ratio.Draw("EP")
                
                # Draw horizontal line at 1
                line = ROOT.TLine(hist.x_min, 1, hist.x_max, 1)
                line.SetLineStyle(2)
                line.Draw("SAME")
            
            # Save canvas
            canvas.SaveAs(f"{self.output_dir}/{hist.name}.pdf")
            canvas.Clear()
            self.logger.info(f"Plot saved: {hist.name}.pdf")
    
    def _set_atlas_style(self) -> None:
        """Set ATLAS plot style."""
        style = ROOT.TStyle("ATLAS", "ATLAS style")
        
        # Canvas
        style.SetCanvasBorderMode(0)
        style.SetCanvasColor(ROOT.kWhite)
        
        # Pad
        style.SetPadBorderMode(0)
        style.SetPadColor(ROOT.kWhite)
        style.SetPadGridX(False)
        style.SetPadGridY(False)
        style.SetGridColor(ROOT.kBlack)
        style.SetGridStyle(3)
        style.SetGridWidth(1)
        
        # Frame
        style.SetFrameBorderMode(0)
        style.SetFrameFillColor(ROOT.kWhite)
        style.SetFrameFillStyle(0)
        style.SetFrameLineColor(ROOT.kBlack)
        style.SetFrameLineStyle(0)
        style.SetFrameLineWidth(1)
        
        # Histogram
        style.SetHistLineColor(ROOT.kBlack)
        style.SetHistLineStyle(0)
        style.SetHistLineWidth(1)
        
        # Options
        style.SetOptStat(0)
        style.SetOptTitle(0)
        
        # Margins
        style.SetPadTopMargin(0.05)
        style.SetPadBottomMargin(0.16)
        style.SetPadLeftMargin(0.16)
        style.SetPadRightMargin(0.08)  # Increased from 0.05 to accommodate scientific notation
        
        # Font
        font = 42  # Helvetica
        style.SetLabelFont(font, "xyz")
        style.SetTitleFont(font, "xyz")
        style.SetTextFont(font)
        style.SetLegendFont(font)
        
        style.cd()
        ROOT.gROOT.ForceStyle()
    
    def _draw_atlas_label(self, 
                         text: str = "Internal",
                         x: float = 0.2,
                         y: float = 0.85,
                         has_ratio: bool = False) -> None:
        """Draw ATLAS label."""
        label = ROOT.TLatex()
        label.SetNDC()
        label.SetTextFont(72)
        
        # Adjust text size based on pad type
        if has_ratio:
            label.SetTextSize(0.06)  # Slightly smaller than before
            spacing = 0.15  # Increased spacing for ratio plots
        else:
            label.SetTextSize(0.05)  # Original size for single pad
            spacing = 0.17  # Original spacing for single pad
            
        label.DrawLatex(x, y, "ATLAS")
        label.SetTextFont(42)
        label.DrawLatex(x + spacing, y, text)
    
    def _configure_pad_margins(self, pad, is_upper: bool = False) -> None:
        """Configure pad margins consistently."""
        pad.SetLeftMargin(0.16)
        pad.SetRightMargin(0.08)
        
        if is_upper:
            pad.SetBottomMargin(0.03)
        else:
            pad.SetTopMargin(0.03)
            pad.SetBottomMargin(0.35)
    
    def _configure_axes(self, hist, main_hist, has_ratio: bool) -> None:
        """Configure axis properties consistently."""
        main_hist.GetXaxis().SetTitle(hist.x_label)
        main_hist.GetYaxis().SetTitle(hist.y_label)
        
        # Y-axis settings
        main_hist.GetYaxis().SetLabelSize(0.045)
        main_hist.GetYaxis().SetTitleSize(0.05)
        main_hist.GetYaxis().SetTitleOffset(1.5)
        
        # X-axis settings depend on ratio
        if has_ratio:
            main_hist.GetXaxis().SetLabelSize(0)
            main_hist.GetXaxis().SetTitleSize(0)
        else:
            main_hist.GetXaxis().SetLabelSize(0.045)
            main_hist.GetXaxis().SetTitleSize(0.05)
        
        # Prevent label overlap
        main_hist.GetXaxis().SetMaxDigits(3)
        if hist.log_y:
            main_hist.GetYaxis().SetMaxDigits(3)
            main_hist.GetYaxis().SetNdivisions(505)
        else:
            main_hist.GetYaxis().SetNdivisions(510)
    
    def _configure_ratio_plot(self, h_ratio, hist) -> None:
        """Configure ratio plot properties."""
        h_ratio.SetLineColor(ROOT.kBlack)
        h_ratio.SetMarkerStyle(20)
        h_ratio.SetMarkerColor(ROOT.kBlack)
        
        # Set axis labels and ranges
        h_ratio.GetXaxis().SetTitle(hist.x_label)
        h_ratio.GetYaxis().SetTitle(hist.ratio_config.y_label)
        h_ratio.GetYaxis().SetRangeUser(hist.ratio_config.y_min, hist.ratio_config.y_max)
        
        # Adjust sizes for ratio panel
        h_ratio.GetXaxis().SetLabelSize(0.10)
        h_ratio.GetXaxis().SetTitleSize(0.12)
        h_ratio.GetYaxis().SetLabelSize(0.10)
        h_ratio.GetYaxis().SetTitleSize(0.11)
        h_ratio.GetYaxis().SetTitleOffset(0.8)
        
        # Prevent label overlap
        h_ratio.GetXaxis().SetMaxDigits(3)
        h_ratio.GetYaxis().SetMaxDigits(2)
        h_ratio.GetXaxis().SetNdivisions(505)
        h_ratio.GetYaxis().SetNdivisions(505)

    def _merge_histograms(self, hist: Histogram) -> Dict[str, ROOT.TH1F]:
        """Merge histograms from processes with the same name."""
        merged = {}
        
        # Group histograms by process name
        for proc in self.processes:
            if proc.name not in merged:
                # Clone first histogram for this process
                merged[proc.name] = hist.histograms[proc.name].Clone()
            else:
                # Add subsequent histograms
                temp = hist.histograms[proc.name].Clone()
                merged[proc.name].Add(temp)
        
        return merged
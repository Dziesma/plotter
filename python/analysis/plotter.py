from typing import Optional, List, Dict, Union, Tuple
import ROOT
import os
import logging
from .process import Process, ProcessTemplate
from .histogram import Histogram
from .styles import ErrorBandStyle
from .logger import package_logger


class Plotter:
    def __init__(self, output_dir: str = "plots", weight: str = "1", log_level: int = logging.INFO):
        """Initialize the plotter with ATLAS style settings."""

        # Set up logger
        self.logger = package_logger.get_logger("plotter")
        self.logger.setLevel(log_level)
        self.logger.info("Plotter initialized")

        # Suppress ROOT info messages
        ROOT.gROOT.SetBatch(True)  # Run in batch mode
        ROOT.gErrorIgnoreLevel = ROOT.kWarning  # Only show warnings and above

        # Set up processes and histograms
        self.processes: List[Process] = []
        self.unique_processes: List[ProcessTemplate] = []
        self.histograms: List[Histogram] = []
        self.output_dir = output_dir
        self.weight = weight
        
        # Set ATLAS style
        self._set_atlas_style()

    
    def add_process(self, process: Process) -> None:
        """Add a process to the plotter."""

        # Look for matching process template
        process_template = next((p for p in self.unique_processes if p.name == process.name), None)
        if not process_template:
            # Append process template if not already present
            self.unique_processes.append(ProcessTemplate(process.name, process.color, process.stack, process.error_style))
        else:
            # Throw warning if process template already exists with different color or stack setting
            if process.color != process_template.color:
                self.logger.warning(f"Process {process.name} already exists with different color. Skipping color update from {process.file_path}:{process.tree_name}.")
            if process.stack != process_template.stack:
                self.logger.warning(f"Process {process.name} already exists with different stack setting. Skipping stack setting update from {process.file_path}:{process.tree_name}.")
            if process.error_style != process_template.error_style:
                self.logger.warning(f"Process {process.name} already exists with different error style. Skipping error style update from {process.file_path}:{process.tree_name}.")

        # Add the process to the plotter
        self.processes.append(process)
        self.logger.info(f"Added process {process.name} from {process.file_path}:{process.tree_name} to plotter")
    
    
    def add_histogram(self, histogram: Histogram) -> None:
        """Add a histogram configuration to the plotter."""

        # Check if the histogram is already in the plotter
        if histogram.name in [h.name for h in self.histograms]:
            self.logger.warning(f"Histogram {histogram.name} already exists in plotter. Will overwrite existing histogram.")
            self.histograms = [h for h in self.histograms if h.name != histogram.name]

        # Add the histogram to the plotter
        self.histograms.append(histogram)
        self.logger.info(f"Added histogram {histogram.name} to plotter")


    def run(self) -> None:
        """Full pipeline ntuples to fancy plots."""
  
        # Create output directory
        if os.path.exists(self.output_dir):
            self.logger.warning(f"Output directory {self.output_dir} already exists. Plots will be saved in this directory.")
        os.makedirs(self.output_dir, exist_ok=True) 

        # Make hists
        self._make_hists()

        # Merge hists
        for hist in self.histograms:
            hist.merged_histograms = self._merge_hists(hist)
        self.logger.info("Histograms merged")

        output_file = ROOT.TFile(os.path.join(self.output_dir, "merged_histograms.root"), "RECREATE")
        for hist in self.histograms:
            for proc in self.unique_processes:
                if proc.name in hist.merged_histograms:
                    hist.merged_histograms[proc.name].Write(f"{hist.name}_{proc.name}")
        output_file.Close()
        self.logger.info("Merged histograms saved to merged_histograms.root")

        # Make plots
        self._make_plots()
        self.logger.info("All plots created")


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
        style.SetPadRightMargin(0.08)
        
        # Font
        font = 42  # Helvetica
        style.SetLabelFont(font, "xyz")
        style.SetTitleFont(font, "xyz")
        style.SetTextFont(font)
        style.SetLegendFont(font)
        
        ROOT.gStyle = style
        ROOT.gROOT.SetStyle("ATLAS")
        ROOT.gROOT.ForceStyle()


    def _make_hists(self) -> None:
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
                
                # Add weight and variable as columns to the dataframe
                df = df.Define("total_weight", weight)
                df = df.Define("plot_var", hist.variable)
                
                # Book histogram with defined columns
                h = df.Histo1D(h_model, "plot_var", "total_weight")
                actions.append(h)
                
                # Store in histogram object
                hist.histograms.append((proc, h))
        
        # Process all actions in parallel
        self.logger.info("Launching booked RDataFrame actions. This may take a while...")
        ROOT.RDF.RunGraphs(actions)
        self.logger.info("RDataFrame actions processed. Hists created.")


    def _merge_hists(self, hist: Histogram) -> Dict[str, ROOT.TH1F]:
        """Merge histograms from processes with the same name."""
        merged = {}
        
        # Group histograms by process name
        for proc, h in hist.histograms:
            if proc.name not in merged:
                # Clone first histogram for this process
                merged[proc.name] = h.Clone()
            else:
                # Add subsequent histograms
                merged[proc.name].Add(h.Clone())

        # Check if merged histograms are consistent with self.unique_processes excluding processes included/excluded in hist.histograms
        if hist.include_processes is not None:  
            expected_process_names = [p.name for p in self.unique_processes if p.name in hist.include_processes]
        elif hist.exclude_processes is not None:
            expected_process_names = [p.name for p in self.unique_processes if p.name not in hist.exclude_processes]
        else:
            expected_process_names = [p.name for p in self.unique_processes]
        merged_process_names = list(merged.keys())
        if expected_process_names != merged_process_names:
            self.logger.error(f"Expected processes do not match merged histograms: {expected_process_names} != {merged_process_names}")

        return merged


    def _make_plots(self) -> None:
        """Create and save all plots."""
        for hist in self.histograms:

            # Create canvas
            canvas_name = f"canvas_{hist.name}"
            canvas = ROOT.TCanvas(canvas_name, canvas_name, 800, 900)

            # Configure pads/canvas
            if hist.ratio_config:
                upper_pad, lower_pad = self._configure_pads(canvas, hist)
                if not upper_pad or not lower_pad:
                    continue
                upper_pad.cd()
            else:
                canvas.SetRightMargin(0.12) #TODO: configure canvas function
                if hist.log_y:
                    canvas.SetLogy()
                canvas.cd()

            # Format histograms, create blueprint histogram
            self._format_hists(hist.merged_histograms)
            blueprint = list(hist.merged_histograms.values())[0].Clone()
            blueprint.Reset()
            blueprint.Draw()

            # Create legend with adjusted position and size
            legend = ROOT.TLegend(0.70, 0.70, 0.90, 0.90)
            legend.SetBorderSize(0)
            legend.SetFillStyle(0)

            # Separate stacked and unstacked processes
            stacked_hists, unstacked_hists = self._separate_hists(hist.merged_histograms)

            # Draw histograms
            if len(stacked_hists) > 0:
                cached_stack, cached_stack_total = self._draw_stack(hist, stacked_hists, legend)
            if len(unstacked_hists) > 0:
                cached_hists = self._draw_unstacked_hists(unstacked_hists, legend)

            # Configure axes
            max_height = max([h.GetMaximum() for h in cached_hists] + [cached_stack_total.GetMaximum()])
            self._configure_axes(hist, blueprint, max_height)

            # Draw legend
            legend.Draw()
            
            # Draw ATLAS label
            self._draw_atlas_label(has_ratio=bool(hist.ratio_config))
            
            # Handle ratio plot if configured
            if hist.ratio_config: #TODO: move parts to separate functions
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
                    h_num = hist.merged_histograms[hist.ratio_config.numerator].Clone()
                
                # Get denominator histogram
                if hist.ratio_config.denominator == "stack":
                    if not stacked_hists:
                        self.logger.error("Stack requested for ratio denominator but no stacked histograms found")
                        continue
                    h_den = stacked_hists[0].Clone()
                    for h in stacked_hists[1:]:
                        h_den.Add(h)
                else:
                    h_den = hist.merged_histograms[hist.ratio_config.denominator].Clone()
                
                # Create ratio histogram
                h_ratio = h_num.Clone("ratio")
                h_ratio.Divide(h_num, h_den, 1.0, 1.0, hist.ratio_config.error_option) #TODO: error_option not using denominator error
                
                # Configure ratio panel axes
                self._configure_ratio_axes(h_ratio, hist)
                
                # Draw ratio points using numerator process style
                if hist.ratio_config.numerator == "stack":
                    error_style = hist.stack_error_style
                    if error_style == ErrorBandStyle.POINTS:
                        h_ratio.SetMarkerColor(ROOT.kGray)
                        h_ratio.SetLineColor(ROOT.kGray)
                        h_ratio.Draw("E X0")
                    elif error_style == ErrorBandStyle.HATCHED:
                        self.logger.error("Hatched error style not yet implemented for stack numerator ratio plots")
                        continue
                    else:
                        self.logger.error(f"Invalid error style: {error_style}")
                        continue
                else:
                    proc = next(p for p in self.unique_processes if p.name == hist.ratio_config.numerator)
                    if proc.error_style == ErrorBandStyle.POINTS:
                        h_ratio.SetMarkerStyle(20)
                        h_ratio.SetMarkerColor(proc.color)
                        h_ratio.Draw("E X0")
                    elif proc.error_style == ErrorBandStyle.HATCHED:
                        self.logger.error("Hatched error style not yet implemented for process-specific ratio plots")
                        continue
                    else:
                        self.logger.error(f"Invalid error style: {proc.error_style}")
                        continue

                # Draw stack errors centered at 1.0 if denominator is stack
                if hist.ratio_config.denominator == "stack":
                    h_stack_errors = h_den.Clone()
                    for i in range(1, h_stack_errors.GetNbinsX() + 1):
                        if h_stack_errors.GetBinContent(i) > 0:
                            h_stack_errors.SetBinContent(i, 1.0)
                            h_stack_errors.SetBinError(i, h_den.GetBinError(i) / h_den.GetBinContent(i))
                    h_stack_errors.SetFillColor(ROOT.kBlack)
                    h_stack_errors.SetFillStyle(3004)
                    h_stack_errors.SetMarkerStyle(0)
                    h_stack_errors.SetMarkerSize(0)
                    h_stack_errors.Draw("E2 SAME")
                
                    # Draw horizontal line at 1
                    line = ROOT.TLine(hist.x_min, 1, hist.x_max, 1)
                    line.SetLineStyle(2)
                    line.Draw("SAME")
            
            # Save canvas
            canvas.Update()
            canvas.SaveAs(f"{self.output_dir}/{hist.name}.pdf")
            canvas.Close()
            self.logger.info(f"Plot saved: {hist.name}.pdf")


    def _configure_pads(self, canvas: ROOT.TCanvas, hist: Histogram) -> Tuple[ROOT.TPad, ROOT.TPad]:
        """Configure pads."""

        # Configure upper pad
        upper_pad = ROOT.TPad(f"upper_pad_{hist.name}", f"upper_pad_{hist.name}", 0, 0.3, 1, 1)
        if not upper_pad:
            self.logger.error(f"Upper pad not created for histogram {hist.name}. Skipping plot.")
            return None, None
        upper_pad.SetLeftMargin(0.16)
        upper_pad.SetRightMargin(0.08)
        upper_pad.SetBottomMargin(0.03)
        upper_pad.Draw()

        # Configure lower pad
        lower_pad = ROOT.TPad(f"lower_pad_{hist.name}", f"lower_pad_{hist.name}", 0, 0, 1, 0.3)
        if not lower_pad:
            self.logger.error(f"Lower pad not created for histogram {hist.name}. Skipping plot.")
            return None, None
        lower_pad.SetLeftMargin(0.16)
        lower_pad.SetRightMargin(0.08)
        lower_pad.SetTopMargin(0.03)
        lower_pad.SetBottomMargin(0.35)
        lower_pad.Draw()
        
        # Set log y if configured
        if hist.log_y:
            upper_pad.SetLogy()

        return upper_pad, lower_pad


    def _format_hists(self, merged_hists: Dict[str, ROOT.TH1F]) -> None:
        """Format histograms."""
        for proc_name, h in merged_hists.items():

            # Find process template
            proc = next((p for p in self.unique_processes if p.name == proc_name), None)
            if not proc:
                self.logger.error(f"Process template {proc_name} not found when formatting merged histogram {h.GetName()}")
                continue

            # Set style
            h.SetLineColor(proc.color)
            if proc.stack:
                h.SetFillColor(proc.color)
            else:
                h.SetFillStyle(0)


    def _separate_hists(self, merged_hists: Dict[str, ROOT.TH1F]) -> Tuple[List[ROOT.TH1F], List[ROOT.TH1F]]:
        """Separate stacked and unstacked processes."""
        stacked_hists = []
        unstacked_hists = []
        for proc in self.unique_processes:
            if proc.name in merged_hists:
                h = merged_hists[proc.name].Clone()
                if proc.stack:
                    stacked_hists.append(h)
                else:
                    unstacked_hists.append((proc, h))

        stacked_hists.sort(key=lambda h: h.Integral())
        unstacked_hists.sort(key=lambda u: u[1].Integral())
        return stacked_hists, unstacked_hists


    def _draw_stack(self, hist: Histogram, stacked_hists: List[ROOT.TH1F], legend: ROOT.TLegend) -> Tuple[ROOT.THStack, ROOT.TH1F]:
        """Draw stack. The stack and total histogram must be returned for ROOT to draw them."""

        # Create stack
        stack = ROOT.THStack("stack", "")
        first_hist = True
        for h in stacked_hists:
            if first_hist:
                total_hist = h.Clone()
                first_hist = False
            else:
                total_hist.Add(h)
            stack.Add(h)
            legend.AddEntry(h, h.GetName(), "f")
        stack.Draw("HIST SAME")

        # Draw stack error bands
        if hist.stack_error_style == ErrorBandStyle.NONE:
            return total_hist
        elif hist.stack_error_style == ErrorBandStyle.HATCHED:
            total_hist.SetLineWidth(0)
            total_hist.SetMarkerSize(0)
            total_hist.SetFillStyle(3004)
            total_hist.SetFillColor(ROOT.kBlack)
            draw_option = "E2 SAME"
            legend_option = "f"
        else:
            self.logger.error(f"Invalid stack error style: {hist.stack_error_style} for hist {hist.name}. Won't draw stack error bands.")
            return total_hist 
        total_hist.Draw(draw_option)
        legend.AddEntry(total_hist, "Stat. Unc.", legend_option)
        
        return stack, total_hist


    def _draw_unstacked_hists(self, unstacked_hists: List[Tuple[Process, ROOT.TH1F]], legend: ROOT.TLegend) -> List[ROOT.TH1F]:
        """Draw unstacked histograms."""
        cached_hists = []
        for proc, h in unstacked_hists:
            h.SetLineColor(proc.color)
            h.SetMarkerColor(proc.color)
            if proc.error_style == ErrorBandStyle.NONE:
                draw_options = "HIST"
                legend_option = "l"
            elif proc.error_style == ErrorBandStyle.HATCHED:
                draw_options = "HIST"   
                legend_option = "l"
                self.logger.error(f"Error band style {proc.error_style} not yet implemented for unstacked histograms. Drawing with error band style NONE.")
            elif proc.error_style == ErrorBandStyle.POINTS:
                draw_options = "E X0"
                legend_option = "p"
            else:
                draw_options = "HIST"
                legend_option = "l"
                self.logger.error(f"Invalid error style: {proc.error_style}. Drawing with error band style NONE.")
            h.Draw(draw_options + " SAME")
            if legend_option:
                legend.AddEntry(h, proc.name, legend_option)
            cached_hists.append(h)
        return cached_hists


    def _configure_axes(self, hist, blueprint, max_height: float) -> None:
        """Configure axis properties consistently."""

        # Set axis labels
        blueprint.GetXaxis().SetTitle(hist.x_label)
        blueprint.GetYaxis().SetTitle(hist.y_label)
        
        # Y-axis settings
        blueprint.GetYaxis().SetLabelSize(0.045)
        blueprint.GetYaxis().SetTitleSize(0.05)
        blueprint.GetYaxis().SetTitleOffset(1.5)
        
        # X-axis settings depend on ratio
        if hist.ratio_config:
            blueprint.GetXaxis().SetLabelSize(0)
            blueprint.GetXaxis().SetTitleSize(0)
        else:
            blueprint.GetXaxis().SetLabelSize(0.045)
            blueprint.GetXaxis().SetTitleSize(0.05)
        
        # Prevent label overlap
        blueprint.GetXaxis().SetMaxDigits(3)
        if hist.log_y:
            blueprint.GetYaxis().SetMaxDigits(3)
            blueprint.GetYaxis().SetNdivisions(505)
        else:
            blueprint.GetYaxis().SetNdivisions(510)
        
        # Set maximum and minimum to avoid legend overlap
        if hist.y_min is not None:
            blueprint.SetMinimum(hist.y_min)
        if hist.log_y:
            blueprint.SetMaximum(max_height * 10)
        else:
            blueprint.SetMaximum(max_height * 1.4)


    def _draw_atlas_label(self, text: str = "Internal", x: float = 0.2, y: float = 0.85, has_ratio: bool = False) -> None:
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
    
    
    def _configure_ratio_axes(self, h_ratio, hist) -> None:
        """Configure ratio plot axes."""
        
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

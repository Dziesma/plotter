from analysis.process import Process
from analysis.histogram import Histogram, RatioConfig
from analysis.plotter import Plotter
from analysis.styles import ErrorBandStyle
import ROOT

# Create processes
Wjets_mc23a_no_veto = Process(
    name="Wjets_Run3_no_veto",
    file_path="/data/gkehris/BadMuonVetoAnalysis/merged/no_veto/Wjets_mc23a_Run3_merged.root",
    tree_name="LJAlgo/nominal",
    color=ROOT.kRed+1,
    stack=True
)

Wjets_mc23d_no_veto = Process(
    name="Wjets_Run3_no_veto",
    file_path="/data/gkehris/BadMuonVetoAnalysis/merged/no_veto/Wjets_mc23d_Run3_merged.root",
    tree_name="LJAlgo/nominal",
    color=ROOT.kRed+1,
    stack=True
)

Zjets_mc23a_no_veto = Process(
    name="Zjets_Run3_no_veto",
    file_path="/data/gkehris/BadMuonVetoAnalysis/merged/no_veto/Zjets_mc23a_Run3_merged.root",
    tree_name="LJAlgo/nominal",
    color=ROOT.kBlue+1,
    stack=True,
    error_style="points"
)

Zjets_mc23d_no_veto = Process(
    name="Zjets_Run3_no_veto",
    file_path="/data/gkehris/BadMuonVetoAnalysis/merged/no_veto/Zjets_mc23d_Run3_merged.root",
    tree_name="LJAlgo/nominal",
    color=ROOT.kBlue+1,
    stack=True,
    error_style="points"
)

Wjets_mc23a_w_veto = Process(
    name="Run3_w_veto",
    file_path="/data/gkehris/BadMuonVetoAnalysis/merged/w_veto/Wjets_mc23a_Run3_merged.root",
    tree_name="LJAlgo/nominal",
    color=ROOT.kBlack,
    stack=False
)

Wjets_mc23d_w_veto = Process(
    name="Run3_w_veto",
    file_path="/data/gkehris/BadMuonVetoAnalysis/merged/w_veto/Wjets_mc23d_Run3_merged.root",
    tree_name="LJAlgo/nominal",
    color=ROOT.kBlack,
    stack=False
)

Zjets_mc23a_w_veto = Process(
    name="Run3_w_veto",
    file_path="/data/gkehris/BadMuonVetoAnalysis/merged/w_veto/Zjets_mc23a_Run3_merged.root",
    tree_name="LJAlgo/nominal",
    color=ROOT.kBlack,
    stack=False
)

Zjets_mc23d_w_veto = Process(
    name="Run3_w_veto",
    file_path="/data/gkehris/BadMuonVetoAnalysis/merged/w_veto/Zjets_mc23d_Run3_merged.root",
    tree_name="LJAlgo/nominal",
    color=ROOT.kBlack,
    stack=False
)

# Create ratio configuration
ratio_config = RatioConfig(
    numerator="Run3_w_veto",
    denominator="stack",
    y_label="veto eff.",
    y_min=0.9,
    y_max=1.1,
    error_option="B"  # "B" for binomial, "" for standard error propagation
)

# Create histogram configurations
pt_hist = Histogram(
    name="lepton_pt",
    variable="lepton1_pt",
    bins=15,
    x_min=0,
    x_max=1500,
    x_label="Lepton p_{T} [GeV]",
    y_min=1.0,
    selection="lepton1_pt > 25 && abs(lepton1_eta) < 2.5",
    log_y=True,
    stack_error_style=ErrorBandStyle.HATCHED,
    ratio_config=ratio_config
)

mass_hist = Histogram(
    name="invariant_mass",
    variable="sqrt(2 * lepton1_pt * jet1_pt * (cosh(lepton1_eta - jet1_eta) - cos(lepton1_phi - jet1_phi)))",
    bins=16,
    x_min=0,
    x_max=4000,
    x_label="m_{lj} [GeV]",
    y_min=1.0,
    selection="1",
    log_y=True,
    stack_error_style=ErrorBandStyle.HATCHED,
    ratio_config=ratio_config
)

# Create plotter and add processes and histograms
plotter = Plotter(weight="mcEventWeight*weight_gen*weight_lumi*weight_norm*weight_singleleptonTrigSF*weight_lepton*weight_pileup*weight_btag*weight_jvt*beamSpotWeight", output_dir="run3") #"mcEventWeight*weight_gen*weight_lumi*weight_norm*weight_singleleptonTrigSF*weight_lepton*weight_pileup*weight_btag*weight_jvt*beamSpotWeight")

plotter.add_process(Wjets_mc23a_no_veto)
plotter.add_process(Wjets_mc23d_no_veto)
plotter.add_process(Zjets_mc23a_no_veto)
plotter.add_process(Zjets_mc23d_no_veto)
plotter.add_process(Wjets_mc23a_w_veto)
plotter.add_process(Wjets_mc23d_w_veto)
plotter.add_process(Zjets_mc23a_w_veto)
plotter.add_process(Zjets_mc23d_w_veto)

plotter.add_histogram(pt_hist)
plotter.add_histogram(mass_hist)

# Run analysis and create plots
plotter.run() 
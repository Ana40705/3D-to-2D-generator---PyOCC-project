import os
import re
import tempfile
import zipfile
import io
import streamlit as st
import fitz  # PyMuPDF
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# OpenCASCADE Imports
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.IGESControl import IGESControl_Reader
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_EDGE
from OCC.Core.BRepAdaptor import BRepAdaptor_Curve
from OCC.Core.GeomAbs import GeomAbs_Circle
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCC.Core.HLRAlgo import HLRAlgo_Projector
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax2
from OCC.Core.GCPnts import GCPnts_QuasiUniformDeflection
from OCC.Core.TopoDS import TopoDS_Compound
from OCC.Core.BRep import BRep_Builder

# --- GLOBAL CONFIG ---
ViewsConfig = {
    'Isometric': {'eye': gp_Pnt(200, 200, 200), 'view_dir': gp_Dir(-1, -1, -1), 'up_dir': gp_Dir(0, 0, 1)},
    'Top':       {'eye': gp_Pnt(0, 0, 1000),    'view_dir': gp_Dir(0, 0, -1),   'up_dir': gp_Dir(0, 1, 0)},
    'Bottom':    {'eye': gp_Pnt(0, 0, -1000),   'view_dir': gp_Dir(0, 0, 1),    'up_dir': gp_Dir(0, 1, 0)},
    'Front':     {'eye': gp_Pnt(0, -1000, 0),   'view_dir': gp_Dir(0, 1, 0),    'up_dir': gp_Dir(0, 0, 1)},
    'Left':      {'eye': gp_Pnt(-1000, 0, 0),   'view_dir': gp_Dir(1, 0, 0),    'up_dir': gp_Dir(0, 0, 1)},
    'Right':     {'eye': gp_Pnt(1000, 0, 0),    'view_dir': gp_Dir(-1, 0, 0),   'up_dir': gp_Dir(0, 0, 1)},
    'Rear':      {'eye': gp_Pnt(0, 1000, 0),    'view_dir': gp_Dir(0, -1, 0),   'up_dir': gp_Dir(0, 0, 1)}
}

# --- CUSTOM CSS INJECTION ---
def inject_custom_css():
    st.markdown("""
        <style>
            /* Main Background and Text */
            .stApp {
                background-color: #0E1117;
                color: #FAFAFA;
            }
            
            /* Headers */
            h1, h2, h3 {
                color: #4B90FF !important; /* Tech Blue */
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            
            /* Customizing the Metric Box (Score) */
            [data-testid="stMetricValue"] {
                color: #00FF88 !important; /* Neon Green for Success */
                font-size: 3rem !important;
                font-weight: 700;
            }
            
            /* Container styling */
            [data-testid="stVerticalBlock"] > div > div {
                border-radius: 8px;
            }
            
            /* Subtler dividers */
            hr {
                border-color: #2D3340 !important;
            }
            
            /* File Uploader styling */
            .stFileUploader {
                border: 2px dashed #4B90FF;
                border-radius: 10px;
                padding: 10px;
                background-color: #1A1F29;
            }
            
            /* Primary Button */
            .stButton > button[kind="primary"] {
                background-color: #4B90FF;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 0.5rem 1rem;
                font-weight: bold;
                transition: background-color 0.3s;
            }
            .stButton > button[kind="primary"]:hover {
                background-color: #3172E0;
            }
        </style>
    """, unsafe_allow_html=True)

# --- BACKEND FUNCTIONS ---

def load_3d_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ['.stp', '.step']:
        reader = STEPControl_Reader()
        if reader.ReadFile(file_path) != 1: return None
        reader.TransferRoots()
        return reader.OneShape()
    elif ext in ['.igs', '.iges']:
        reader = IGESControl_Reader()
        if reader.ReadFile(file_path) != 1: return None
        reader.TransferRoots()
        return reader.OneShape()
    return None

def extract_key_3d_metrology(shape):
    bbox = Bnd_Box()
    brepbndlib.Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    l, w, h = round((xmax-xmin)/10, 2), round((ymax-ymin)/10, 2), round((zmax-zmin)/10, 2)
    holes = []
    exp = TopExp_Explorer(shape, TopAbs_EDGE)
    while exp.More():
        adaptor = BRepAdaptor_Curve(exp.Current())
        if adaptor.GetType() == GeomAbs_Circle:
            diameter_cm = (adaptor.Circle().Radius() * 2) / 10
            if diameter_cm > 0.1: holes.append(round(diameter_cm, 2))
        exp.Next()
    return set(round(x, 2) for x in set([l, w, h] + holes) if x > 0.1)

def extract_pdf_dimensions(pdf_path):
    doc = fitz.open(pdf_path)
    all_text = ""
    for page in doc: all_text += page.get_text()
    raw_numbers = re.findall(r'\d+\.\d+', all_text)
    doc.close()
    return set(float(num) for num in raw_numbers)

def get_single_view_lines(shape, view_name):
    config = ViewsConfig[view_name]
    projector = HLRAlgo_Projector(gp_Ax2(config['eye'], config['view_dir'], config['up_dir']))
    hlr = HLRBRep_Algo()
    hlr.Add(shape); hlr.Projector(projector); hlr.Update(); hlr.Hide()
    hlr_shapes = HLRBRep_HLRToShape(hlr)
    builder = BRep_Builder()
    combined = TopoDS_Compound()
    builder.MakeCompound(combined)
    for s in [hlr_shapes.VCompound(), hlr_shapes.OutLineVCompound(), hlr_shapes.Rg1LineVCompound()]:
        if s is not None and not s.IsNull(): builder.Add(combined, s)
    return combined

def extract_2d_lines(shape, deflection=0.1):
    lines = []
    if shape is None or shape.IsNull(): return lines
    exp = TopExp_Explorer(shape, TopAbs_EDGE)
    while exp.More():
        adaptor = BRepAdaptor_Curve(exp.Current())
        discretizer = GCPnts_QuasiUniformDeflection(adaptor, deflection)
        x_pts, y_pts = [], []
        for i in range(1, discretizer.NbPoints() + 1):
            p = discretizer.Value(i)
            x_pts.append(p.X()); y_pts.append(p.Y())
        lines.append((x_pts, y_pts))
        exp.Next()
    return lines

def draw_baseline_dimensions(ax, lines, view_name):
    if view_name == 'Isometric' or not lines: return
    all_x, all_y, circles = [], [], []
    for x, y in lines:
        if len(x) <= 3:
            all_x.extend(x); all_y.extend(y)
        else:
            cx, cy = sum(x)/len(x), sum(y)/len(y)
            r = ((x[0]-cx)**2 + (y[0]-cy)**2)**0.5
            if r > 2.0: circles.append((cx, cy, r))
            all_x.extend(x); all_y.extend(y)

    if not all_x: return
    min_x, min_y, max_x, max_y = min(all_x), min(all_y), max(all_x), max(all_y)
    sig_x, sig_y = set(), set()
    for x, y in lines:
        if len(x) <= 3:
            for px, py in zip(x, y):
                sig_x.add(round(px, 1)); sig_y.add(round(py, 1))
    for cx, cy, r in circles:
        sig_x.add(round(cx, 1)); sig_y.add(round(cy, 1))

    sig_x = sorted([x for x in sig_x if x > min_x + 1.0])
    sig_y = sorted([y for y in sig_y if y > min_y + 1.0])
    step = max(max_x - min_x, max_y - min_y) * 0.15
    ext_start_gap = step * 0.2
    bg_style = dict(facecolor='white', edgecolor='none', alpha=0.9, pad=0.5)

    y_level = max_y + step
    for px in sig_x:
        dist_cm = (px - min_x) / 10
        ax.plot([min_x, min_x], [max_y + ext_start_gap, y_level + ext_start_gap], color='black', lw=0.5)
        ax.plot([px, px], [max_y + ext_start_gap, y_level + ext_start_gap], color='black', lw=0.5)
        ax.annotate('', xy=(min_x, y_level), xytext=(px, y_level), arrowprops=dict(arrowstyle='<->', color='black', lw=0.8))
        ax.text((min_x + px)/2, y_level + (step*0.1), f"{dist_cm:.2f}", ha='center', va='bottom', fontsize=8, bbox=bg_style)
        y_level += step * 0.7

    x_level = max_x + step
    for py in sig_y:
        dist_cm = (py - min_y) / 10
        ax.plot([max_x + ext_start_gap, x_level + ext_start_gap], [min_y, min_y], color='black', lw=0.5)
        ax.plot([max_x + ext_start_gap, x_level + ext_start_gap], [py, py], color='black', lw=0.5)
        ax.annotate('', xy=(x_level, min_y), xytext=(x_level, py), arrowprops=dict(arrowstyle='<->', color='black', lw=0.8))
        ax.text(x_level - (step*0.1), (min_y + py)/2, f"{dist_cm:.2f}", ha='right', va='center', rotation=90, fontsize=8, bbox=bg_style)
        x_level += step * 0.7

    for cx, cy, r in circles:
        ax.plot([cx-r*1.5, cx+r*1.5], [cy, cy], color='black', lw=0.4, ls='-.')
        ax.plot([cx, cx], [cy-r*1.5, cy+r*1.5], color='black', lw=0.4, ls='-.')
        r_cm, leader_len = r / 10, r * 3
        target_x, target_y = cx - (r * 0.707), cy + (r * 0.707) 
        shoulder_x, shoulder_y = target_x - leader_len, target_y + leader_len
        ax.annotate('', xy=(target_x, target_y), xytext=(shoulder_x, shoulder_y), arrowprops=dict(arrowstyle='->', color='black', lw=0.8))
        ax.plot([shoulder_x, shoulder_x - leader_len*0.8], [shoulder_y, shoulder_y], color='black', lw=0.8)
        ax.text(shoulder_x - leader_len*0.4, shoulder_y + (r*0.2), f"Ø{r_cm*2:.2f}", ha='center', va='bottom', fontsize=8, bbox=bg_style)

def draw_isometric_preview(shape):
    lines = extract_2d_lines(get_single_view_lines(shape, 'Isometric'))
    
    # Use a dark theme for the Matplotlib plot to match the UI
    fig, ax = plt.subplots(figsize=(6, 6), facecolor='#0E1117') 
    ax.set_facecolor('#0E1117')
    ax.axis('off')
    
    for x, y in lines: 
        ax.plot(x, y, color='#4B90FF', linewidth=1.5) # Tech Blue lines
        
    ax.set_aspect('equal', adjustable='box')
    return fig

def render_highlighted_pdf(pdf_path, matched_dims, tolerance=0.15):
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    words = page.get_text("words")
    for w in words:
        rect, text = fitz.Rect(w[:4]), w[4]
        nums = re.findall(r'\d+\.\d+', text)
        for num_str in nums:
            val = float(num_str)
            is_match = any(abs(true_dim - val) <= tolerance for true_dim in matched_dims)
            if is_match: page.draw_rect(rect, color=(0, 0.8, 0), width=1.5, fill_opacity=0.2, fill=(0, 1, 0))
            else: page.draw_rect(rect, color=(1, 0, 0), width=1.5, fill_opacity=0.2, fill=(1, 0, 0))
    pix = page.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("png")
    doc.close()
    return img_bytes

def generate_pdf_from_shape(shape, filename, selected_views):
    pdf_output_path = tempfile.mktemp(suffix=".pdf")
    with PdfPages(pdf_output_path) as pdf:
        for view_name in selected_views:
            fig, ax = plt.subplots(figsize=(12, 10))
            fig.suptitle(f"Detail View: {view_name}\nFile: {filename}", fontsize=16)
            ax.axis('on'); ax.set_xticks([]); ax.set_yticks([])
            for spine in ax.spines.values(): spine.set_color('#D3D3D3')
            lines = extract_2d_lines(get_single_view_lines(shape, view_name))
            for x, y in lines: ax.plot(x, y, color='black', linewidth=1.5)
            draw_baseline_dimensions(ax, lines, view_name)
            ax.margins(0.3)
            ax.set_aspect('equal', adjustable='box')
            pdf.savefig(fig, facecolor='white', bbox_inches='tight')
            plt.close(fig)
    
    with open(pdf_output_path, "rb") as f:
        pdf_bytes = f.read()
    
    try: os.remove(pdf_output_path)
    except: pass
    
    return pdf_bytes, pdf_output_path


# --- STREAMLIT FRONTEND ---

st.set_page_config(page_title="CAD Validation Suite", page_icon="📐", layout="wide")

# Apply custom styling
inject_custom_css()

# Enhanced UI Header
st.title("📐 Engineering CAD Suite")
st.markdown("**Professional tools for Model-Based Definition (MBD) validation and automated Blueprint generation.**")
st.divider()

# Create the application Tabs
tab1, tab2 = st.tabs(["🔍 MBD Auditor (3D vs 2D)", "🖨️ Blueprint Generator (Batch Enabled)"])

# ==========================================
# TAB 1: MBD SANITY CHECKER
# ==========================================
with tab1:
    st.subheader("Automated Metrology Quality Assurance")
    st.markdown("Verify that an existing 2D PDF drawing mathematically matches the original 3D CAD geometry.")
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            stp_file = st.file_uploader("1. Upload 3D File (.stp, .igs)", type=["stp", "step", "igs", "iges"], key="auditor_3d")
        with col2:
            pdf_file = st.file_uploader("2. Upload 2D PDF Drawing (.pdf)", type=["pdf"], key="auditor_2d")

    if stp_file and pdf_file:
        tolerance = st.slider("Verification Tolerance (cm)", 0.0, 0.5, 0.15, 0.01)
        
        if st.button("Run Metrology Audit", type="primary", use_container_width=True):
            with st.status("Analyzing Geometry and Extracting Data...", expanded=True) as status:
                st.write("Reading 3D Model...")
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(stp_file.name)[1]) as tmp_stp:
                    tmp_stp.write(stp_file.getvalue())
                    stp_path = tmp_stp.name
                    
                st.write("Scanning PDF OCR...")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                    tmp_pdf.write(pdf_file.getvalue())
                    pdf_path = tmp_pdf.name

                shape = load_3d_file(stp_path)
                if shape:
                    st.write("Calculating Intersections...")
                    key_3d_dims = extract_key_3d_metrology(shape)
                    pdf_dims = extract_pdf_dimensions(pdf_path)

                    matched_dims, missing_from_pdf = set(), set()
                    for true_dim in key_3d_dims:
                        if any(abs(true_dim - pdf_dim) <= tolerance for pdf_dim in pdf_dims): matched_dims.add(true_dim)
                        else: missing_from_pdf.add(true_dim)

                    match_count = len(matched_dims)
                    total_kccs = len(key_3d_dims)
                    score = int((match_count / total_kccs) * 100) if total_kccs > 0 else 0

                    status.update(label="Audit Complete!", state="complete", expanded=False)

                    st.subheader("Audit Results & Basis of Classification")
                    metric_col1, metric_col2 = st.columns([1, 3])
                    with metric_col1: st.metric(label="Match Confidence", value=f"{score}%")
                    with metric_col2:
                        if score == 100: st.success("✅ **PASS:** All dimensions mapped perfectly.")
                        elif score > 50: st.warning("⚠️ **PARTIAL MATCH:** Check missing dimensions.")
                        else: st.error("❌ **FAIL:** Critical mismatch.")

                    res_col1, res_col2 = st.columns(2)
                    with res_col1: st.info(f"**Matched 3D KCCs:** {sorted(list(matched_dims))}")
                    with res_col2:
                        if missing_from_pdf: st.error(f"**Missing 3D KCCs:** {sorted(list(missing_from_pdf))}")
                        else: st.info("**Missing 3D KCCs:** None!")

                    st.divider()
                    st.subheader("Visual Proof")
                    vis_col1, vis_col2 = st.columns(2)
                    with vis_col1:
                        st.markdown("**3D True Geometry**")
                        # The Matplotlib figure now matches the dark theme
                        st.pyplot(draw_isometric_preview(shape))
                    with vis_col2:
                        st.markdown("**2D PDF Feature Map**")
                        st.caption("🟢 **Green** = Verified 3D KCC | 🔴 **Red** = Unmatched / Baseline Dimension")
                        st.image(render_highlighted_pdf(pdf_path, matched_dims, tolerance), use_container_width=True)
                else:
                    status.update(label="File Error", state="error")
                    st.error("Failed to parse the 3D model.")

                try: os.remove(stp_path); os.remove(pdf_path)
                except: pass

# ==========================================
# TAB 2: BLUEPRINT GENERATOR (BATCH PROCESSING)
# ==========================================
with tab2:
    st.subheader("Generate 2D PDF Drawings from 3D Data")
    st.markdown("Upload one or multiple 3D files to automatically generate technical orthographic blueprints.")
    
    with st.container(border=True):
        gen_files = st.file_uploader("Upload 3D File(s) (.stp, .step, .igs, .iges)", 
                                     type=["stp", "step", "igs", "iges"], 
                                     accept_multiple_files=True, 
                                     key="generator_3d")
        
        available_views = ['Isometric', 'Top', 'Bottom', 'Front', 'Rear', 'Left', 'Right']
        selected_views = st.multiselect("Select Output Views to Generate:", available_views, default=['Isometric', 'Top', 'Front', 'Right'])

    if gen_files and selected_views:
        if st.button(f"Generate Blueprints for {len(gen_files)} File(s)", type="primary", use_container_width=True):
            
            # --- SINGLE FILE WORKFLOW ---
            if len(gen_files) == 1:
                gen_file = gen_files[0]
                with st.spinner(f'Processing {gen_file.name}...'):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(gen_file.name)[1]) as tmp_gen:
                        tmp_gen.write(gen_file.read())
                        gen_path = tmp_gen.name
                    
                    shape = load_3d_file(gen_path)
                    if shape:
                        pdf_bytes, _ = generate_pdf_from_shape(shape, gen_file.name, selected_views)
                        
                        st.success("✅ Blueprint Generated Successfully!")
                        
                        st.download_button(
                            label=f"⬇️ Download {gen_file.name} Blueprint (.pdf)",
                            data=pdf_bytes,
                            file_name=f"Blueprint_{os.path.splitext(gen_file.name)[0]}.pdf",
                            mime='application/pdf',
                            use_container_width=True
                        )
                        
                        st.divider()
                        st.subheader("Blueprint Preview (Page 1)")
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_preview:
                            tmp_preview.write(pdf_bytes)
                            preview_path = tmp_preview.name
                        
                        doc = fitz.open(preview_path)
                        page = doc.load_page(0)
                        pix = page.get_pixmap(dpi=150)
                        st.image(pix.tobytes("png"), use_container_width=True)
                        doc.close()
                        
                        try: os.remove(preview_path)
                        except: pass
                        
                    else:
                        st.error(f"Failed to parse {gen_file.name}.")
                    
                    try: os.remove(gen_path)
                    except: pass
                    
            # --- BATCH MULTI-FILE WORKFLOW ---
            else:
                st.info(f"Batch Processing {len(gen_files)} files. This may take a moment...")
                progress_bar = st.progress(0)
                
                zip_buffer = io.BytesIO()
                
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for i, gen_file in enumerate(gen_files):
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(gen_file.name)[1]) as tmp_gen:
                            tmp_gen.write(gen_file.read())
                            gen_path = tmp_gen.name
                        
                        shape = load_3d_file(gen_path)
                        if shape:
                            pdf_bytes, _ = generate_pdf_from_shape(shape, gen_file.name, selected_views)
                            pdf_filename = f"Blueprint_{os.path.splitext(gen_file.name)[0]}.pdf"
                            zip_file.writestr(pdf_filename, pdf_bytes)
                        else:
                            st.warning(f"Skipped {gen_file.name}: Could not parse 3D geometry.")
                        
                        try: os.remove(gen_path)
                        except: pass
                        
                        progress_bar.progress((i + 1) / len(gen_files))
                
                st.success("✅ Batch Generation Complete!")
                
                st.download_button(
                    label="⬇️ Download All Blueprints (.zip)",
                    data=zip_buffer.getvalue(),
                    file_name="Batch_Blueprints.zip",
                    mime="application/zip",
                    use_container_width=True
                )
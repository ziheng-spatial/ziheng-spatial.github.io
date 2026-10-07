---
title: "1:500 Large-Scale Digital Topographic Mapping (Campus & Base)"
date: 2026-10-07
description: "A complete geomatics workflow featuring South NSTR6 data acquisition, rigorous manual traverse adjustment, and CASS vectorization for 1:500 topographical maps."
tags: ["Geomatics", "Topographic Mapping", "AutoCAD", "Traverse Adjustment"]
math: true
---

### 1. Equipment & Geodetic Datum
High-precision topographic mapping requires stringent adherence to geodetic standards and instrument calibration. For this dual-site project (University Campus & Mountain Internship Base), the spatial framework was established using the **CGCS2000 coordinate system** (Gauss-Kruger projection, 39-degree zone) and the **1985 National Height Datum**.

*   **Primary Instrument:** South NSTR6 Total Station (2" angular accuracy, ±2mm+2ppm prism distance accuracy, equipped with dual-axis compensation).
*   **Leveling Instrument:** DS3 Automatic Level with double-faced leveling staves for fourth-order leveling networks.

![South NSTR6 Controller Data Capture](/images/survey-controller.jpg)

### 2. Rigorous Control Survey & Manual Adjustment
Before any topographic detailing begins, a robust control network must be established. We deployed closed and intersecting traverse networks (导线测量) alongside fourth-order leveling routes (四等水准测量). 

To ensure absolute mathematical rigor and verify software outputs, all raw traverse observations (including horizontal angles, vertical angles, and slope distances) underwent strict manual adjustment. This included calculating angle closure errors ($f_\beta$), coordinate increment closures, and distributing corrections via least-squares principles. 

As documented in the handwritten accuracy assessment below, the 20-station traverse achieved an angular closure error of only **42"** (well within the 53.67" tolerance) and an exceptional relative linear closure of **1/65,895**—vastly exceeding the standard 1/2000 requirement for secondary traverses.

*Top: Field Traverse Observation Record | Middle: Inner Office Adjustment Calculation | Bottom: Manual Accuracy Assessment*
![Traverse Record](/images/traverse-record.jpg)
![Calculation Sheet](/images/traverse-calc.jpg)
![Accuracy Assessment](/images/accuracy-assessment.jpg)

### 3. Field Data Acquisition (Detailing)
With the control network mathematically verified, field detailing (碎部测量) was executed using the polar coordinate method. Over 1,900 topographic points were acquired across complex terrains. 

The South NSTR6's reflectorless measurement capability (up to 1000m range) was heavily utilized to capture inaccessible architectural corners and steep terrain features, maintaining a point position RMSE (Root Mean Square Error) of $\le \pm 5$ cm relative to control points. Detailed field sketches were drawn simultaneously to document topological relationships.

### 4. Digital Cartography & CASS Vectorization
The raw coordinate data was exported and processed using **South CASS / AutoCAD**. Following the national cartographic standards (GB/T 20257.1-2017), the points were vectorized into a comprehensive 1:500 digital topographic map (`.dwg`). 

The final deliverables accurately model hydrographic features (e.g., Jixia Lake contouring), dense architectural footprints, vegetation boundaries, and independent utility features, complete with proper map framing, legends, and 0.5m interval contour lines for mountainous sections.

![Topographic Map - Jixia Lake Area](/images/cad-map-lake.jpg)
![Vectorized Parcels](/images/cad-parcels.jpg)
![Vectorized Buildings](/images/cad-buildings.jpg)

---
*Note: This project demonstrates end-to-end proficiency in traditional geomatics field operations, rigorous mathematical error adjustment, and modern CAD-based spatial vectorization.*
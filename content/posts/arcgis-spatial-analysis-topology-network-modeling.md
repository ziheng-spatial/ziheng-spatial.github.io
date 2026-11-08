---
title: "Enterprise Spatial Analysis, Topological Quality Control & Network Accessibility Modeling in ArcGIS"
date: 2026-11-04
draft: false
math: true
tags: ["ArcGIS", "Spatial Analysis", "Geodatabase Topology", "Network Analyst", "Voronoi Tessellation", "Gauss-Kruger Projection", "GF-2 Remote Sensing"]
categories: ["Geospatial Engineering"]
summary: "End-to-end geospatial engineering workflow spanning Gauss-Krüger coordinate transformations, macro-scale hydrographic/transportation spatial queries, parametric 400m stadium buffer modeling, sub-meter GF-2 satellite orthophoto digitization, rank-constrained Geodatabase topological validation, multi-criteria Boolean site selection, and graph-theoretic Dijkstra/Voronoi accessibility analysis."
---

## 1. Geodetic Reference Frames, Gauss-Krüger Projection & Macro-Scale Spatial Queries

High-precision planar metric computation—such as hydrographic channel length integration, arterial corridor clipping, and Euclidean buffer construction—requires transforming spherical geodetic coordinates $(\varphi, \lambda)$ from an earth-referenced datum onto a conformal planar Cartesian grid $(x, y)$.

### 1.1 Evolution of Reference Ellipsoids: Local Astro-Geodetic vs. Geocentric Datums

In surveying and geographic information engineering, national spatial infrastructures have evolved through three distinct geodetic realizations: early local astro-geodetic datums fitted to regional geoid undulations (`Beijing 1954`), nationwide astro-geodetic least-squares net adjustments (`Xian 1980`), and modern three-dimensional dynamic geocentric reference frames (`CGCS2000` and `WGS-84`) aligned with the International Terrestrial Reference Frame (ITRF).

| Geodetic Parameter / Datum Attribute | Beijing 1954 (`GCS_Beijing_1954`) | Xian 1980 (`GCS_Xian_1980`) | CGCS2000 (`GCS_China_2000`) | WGS-84 (`GCS_WGS_1984`) |
| :--- | :--- | :--- | :--- | :--- |
| **Coordinate Frame Type** | Local Astro-Geodetic (2D) | National Astro-Geodetic (2D) | Geocentric Dynamic ITRF97 (3D) | Geocentric Dynamic GNSS (3D) |
| **Reference Ellipsoid** | Krassovsky 1940 | IAG 1975 (GRS 1975) | CGCS2000 Ellipsoid | WGS-84 Ellipsoid |
| **Semi-Major Axis $a\text{ (m)}$** | $6,378,245.0$ | $6,378,140.0$ | $6,378,137.0$ | $6,378,137.0$ |
| **Semi-Minor Axis $b\text{ (m)}$** | $6,356,863.0188$ | $6,356,755.2882$ | $6,356,752.31414$ | $6,356,752.31425$ |
| **Inverse Flattening $1/f$** | $298.3$ | $298.257$ | $298.257222101$ | $298.257223563$ |
| **Datum Origin / Realization** | Pulkovo Observatory | Jingyang, Shaanxi | Earth Center of Mass (ITRF97, 2000.0) | Earth Center of Mass (TRANSIT/GPS) |
| **Defining Physical Constant** | Geometric $(a, f)$ | Geometric $(a, GM, J\_2, \omega)$ | Dynamic $(a, GM, J\_2, \omega)$ | Dynamic $(a, GM, \bar{C}\_{2,0}, \omega)$ |

While `CGCS2000` and `WGS-84` share an identical semi-major axis ($a = 6,378,137.0\text{ m}$), geocentric gravitational constant ($GM = 3.986004418 \times 10^{14}\text{ m}^3/\text{s}^2$), and angular velocity ($\omega = 7.292115 \times 10^{-5}\text{ rad/s}$), their fourth defining parameter differs slightly (`CGCS2000` specifies the dynamic form factor $J\_2 = 1.082629832258 \times 10^{-3}$, whereas `WGS-84` specifies the normalized second-degree zonal harmonic $\bar{C}\_{2,0} = -0.484166774985 \times 10^{-3}$). This induces a minuscule flattening difference $\Delta f = \left|f\_{\text{CGCS2000}} - f\_{\text{WGS84}}\right| \approx 1.64 \times 10^{-11}$, corresponding to a polar semi-minor axis discrepancy of only $\Delta b \approx 0.105\text{ mm}$ and a theoretical horizontal coordinate difference under $0.11\text{ mm}$ at identical epoch realizations.

### 1.2 Conformal Gauss-Krüger (Transverse Mercator) Forward Projection

To Bound linear scale distortion across multi-province engineering zones, thematic and analytical layers are projected via the **Gauss-Krüger conformal cylindrical projection** into either $6^\circ$ zones (e.g., `Xian_1980_GK_Zone_18`, EPSG:2332, central meridian $\lambda\_0 = 105^\circ\text{E}$) or $3^\circ$ zones (e.g., `Beijing_1954_3_Degree_GK_CM_117E`, EPSG:2436, $\lambda\_0 = 117^\circ\text{E}$; and `CGCS2000_3_Degree_GK_CM_108E`, EPSG:4545, $\lambda\_0 = 108^\circ\text{E}$).

Given geodetic latitude $\varphi$, longitude difference $l = \lambda - \lambda\_0$ (in radians), first eccentricity squared $e^2 = (a^2 - b^2)/a^2$, and second eccentricity squared $e^{\prime 2} = (a^2 - b^2)/b^2$, let the prime vertical radius of curvature be $N = a / \sqrt{1 - e^2\sin^2\varphi}$, auxiliary tangent $t = \tan\varphi$, and $\eta^2 = e^{\prime 2}\cos^2\varphi$. The Gauss-Krüger forward transformation mapping $(\varphi, \lambda) \mapsto (x, y)$ with false easting $Y\_0 = 500,000\text{ m}$ is governed by the sixth-order conformal power series:

$$x = X\_0(\varphi) + \frac{N}{2}\sin\varphi\cos\varphi \cdot l^2 + \frac{N}{24}\sin\varphi\cos^3\varphi\left(5 - t^2 + 9\eta^2 + 4\eta^4\right)l^4 + \frac{N}{720}\sin\varphi\cos^5\varphi\left(61 - 58t^2 + t^4\right)l^6$$

$$y = Y\_0 + N\cos\varphi \cdot l + \frac{N}{6}\cos^3\varphi\left(1 - t^2 + \eta^2\right)l^3 + \frac{N}{120}\cos^5\varphi\left(5 - 18t^2 + t^4 + 14\eta^2 - 58\eta^2 t^2\right)l^5$$

Where $X\_0(\varphi) = \int\_0^{\varphi} M(\phi)\,d\phi$ is the meridian arc length from the equator computed from the meridional radius of curvature $M(\phi) = a(1 - e^2)(1 - e^2\sin^2\phi)^{-3/2}$. Within the $3^\circ$ Gauss-Krüger zone ($\left|l\right| \le 1.5^\circ$), the secant/tangent length distortion factor $m = 1 + \frac{y^2}{2R\_m^2} + \mathcal{O}(y^4)$ remains strictly below $1/2,500$, ensuring metric fidelity for regional spatial queries.

### 1.3 Multi-Layer Hydrographic & Arterial Corridor Spatial Overlay Queries

Using the Gauss-Krüger projected coordinate systems (`CGCS2000_3_Degree_GK_CM_108E` for the central-southwest basin and `CGCS2000_3_Degree_GK_CM_117E` for the central-east corridor), two macro-scale vector extraction and statistical aggregation pipelines were executed on national hydrographic and transportation datasets:

1. **Multi-Grade Hydrographic Network Extraction (`Hunan_Sichuan_Rivers_GT100km`)**:
   * **Data Fusion & Projection**: Graded river centerlines (`River_Level_2`: $2,143\text{ reaches}$, `River_Level_4`: $992\text{ reaches}$, and `River_Level_5`: $2,967\text{ reaches}$) were merged into a unified hydrographic feature class ($6,102\text{ total reaches}$) and projected into `CGCS2000_3_Degree_GK_CM_108E` ($\lambda\_0 = 108^\circ\text{E}$).
   * **Spatial Clipping & Attribute Filtering**: Clipping the projected network against the dissolved administrative polygon boundary of Hunan and Sichuan provinces isolated $535\text{ regional river reaches}$. Applying the SQL definition query `"LENGTH" > 100` extracted **$84\text{ major river reaches}$** exceeding $100\text{ km}$, yielding a cumulative channel length of **$12,089.013\text{ km}$**.
2. **Inter-Provincial Corridor Clipping & Summary Statistics (`Hubei_Jiangsu_Corridors_Clip`)**:
   * **Spatial Overlay & Provincial Attribution**: The national trunk corridor layer (`National_Trunk_Corridors`, $189\text{ polyline features}$) and provincial boundary layer (`Provincial_Boundary_Polygon`, $33\text{ polygons}$) were projected into `CGCS2000_3_Degree_GK_CM_117E` ($\lambda\_0 = 117^\circ\text{E}$). Clipping and intersecting against the two-province domain (`ADCODE99 IN (320000, 420000)`) isolated **$8\text{ trunk corridor segments}$** with a combined two-province length of **$850.631\text{ km}$**.

| Query Pipeline / Target Region | Projected Coordinate System | Extracted Features | Segment Breakdown & Representative Trunk Lines | Cumulative Length ($\text{km}$) |
| :--- | :--- | :--- | :--- | :--- |
| **Hunan & Sichuan Rivers ($>100\text{ km}$)** | `CGCS2000_3_Degree_GK_CM_108E` | **$84\text{ reaches}$** | Minjiang ($410.45\text{ km}$), Yalong ($344.23\text{ km}$), Zishui ($343.62\text{ km}$), Jialing ($319.16\text{ km}$), Zitong ($265.60\text{ km}$), Daqu ($258.42\text{ km}$), Dadu ($235.70\text{ km}$), Xiangjiang ($232.18\text{ km}$) | **$12,089.013\text{ km}$** |
| **Hubei Trunk Corridors** | `CGCS2000_3_Degree_GK_CM_117E` | **$6\text{ segments}$** | Handan Line ($308.516\text{ km}$ & $46.032\text{ km}$), Jiaoliu Line ($210.956\text{ km}$ & $7.259\text{ km}$), Xiangyu Line ($42.512\text{ km}$), Jingguang Line ($10.937\text{ km}$) | **$626.212\text{ km}$** |
| **Jiangsu Trunk Corridors** | `CGCS2000_3_Degree_GK_CM_117E` | **$2\text{ segments}$** | Longhai Line ($221.188\text{ km}$), Jinpu Line ($3.231\text{ km}$) | **$224.419\text{ km}$** |
| **Combined Hubei + Jiangsu Total** | `CGCS2000_3_Degree_GK_CM_117E` | **$8\text{ segments}$** | Unified two-province clipped transportation feature class (`Hubei_Jiangsu_Corridors_Clip`) | **$850.631\text{ km}$** |

---

## 2. Parametric Stadium Modeling, Sub-Meter GF-2 Digitization & Geodatabase Topology

### 2.1 Parametric 400m Standard Semi-Circular 8-Lane Athletics Track Modeling

Constructing an engineering-grade **400-meter standard semi-circular 8-lane athletics track** (`Stadium_Track_Lanes`, projected in `CGCS2000_3_Degree_GK_CM_117E`) requires coupling analytical curve-straightaway geometry with sequential concentric ring buffering.

Given an innermost track boundary perimeter of $L\_1 = 400\text{ m}$ and an inner semicircular turn radius of $R\_1 = 36.00\text{ m}$ ($\pi \approx 3.14$), the two semicircular turns account for $C\_1 = 2\pi R\_1 \approx 2 \times 3.14 \times 36 = 226.08\text{ m}$. Subtracting the curved arc length from the $400\text{ m}$ nominal perimeter yields a combined straightaway length of $2S \approx 174.00\text{ m}$, establishing the exact single-side straightaway length:

$$S = \frac{L\_1 - 2\pi R\_1}{2} = \frac{400 - 2 \times 3.14 \times 36}{2} \approx 87.00\text{ m}$$

For an 8-lane stadium track with a uniform radial lane width of $\Delta w = 1.20\text{ m}$, the inner boundary radius of the $n$-th lane ($n \in \lbrace 1, 2, \dots, 8\rbrace$) expands linearly as $R\_n = R\_1 + \Delta w(n - 1) = 36 + 1.2(n - 1)$. Consequently, the theoretical inner boundary perimeter $L\_n$ of the $n$-th lane follows the closed-form progression:

$$L\_n = 2 \times 87 + 2\pi \left[36 + 1.2(n - 1)\right]$$

For instance, evaluating $n = 4$ (Lane 4) yields $L\_4 = 174 + 2\pi(36 + 3.6) = 174 + 79.2\pi \approx 422.81\text{ m}$ ($\approx 423\text{ m}$). Because each lane in `Stadium_Track_Lanes` is modeled as a closed annular polygon bounded between inner radius $R\_n$ and outer radius $R\_{n+1} = R\_n + \Delta w$, the exact planar surface area $A\_n$ of the $n$-th lane polygon is:

$$A\_n = 2 \cdot S \cdot \Delta w + \pi\left[\left(R\_n + \Delta w\right)^2 - R\_n^2\right] = 208.80 + 2.4\pi R\_n + 1.44\pi$$

![Parametric 400m 8-Lane Stadium Track Model](/images/arcgis-stadium-track-buffer.webp)
*Figure 1: Parametric 400m semi-circular 8-lane athletics stadium polygon model (`Stadium_Track_Lanes`, EPSG:4548), displaying full field geometry ($S = 87.00\text{ m}$, $R\_1 = 36.00\text{ m}$, $\Delta w = 1.20\text{ m}$), magnified northern apex annular buffers, and dual-axis perimeter/area telemetry.*

| Lane Index ($n$) | Inner Turn Radius $R\_n\text{ (m)}$ | Outer Turn Radius $R\_{n+1}\text{ (m)}$ | Analytical Perimeter $L\_n\text{ (m)}$ | Rounded Attribute Label | Polygon Surface Area $A\_n\text{ (m}^2\text{)}$ | Total Ring Boundary Perimeter ($\text{m}$) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Lane 1** | $36.00$ | $37.20$ | $400.19$ | `400m` | $484.54$ | $807.56$ |
| **Lane 2** | $37.20$ | $38.40$ | $407.73$ | `408m` | $493.60$ | $822.66$ |
| **Lane 3** | $38.40$ | $39.60$ | $415.27$ | `415m` | $502.66$ | $837.77$ |
| **Lane 4** | $39.60$ | $40.80$ | $422.81$ | `423m` | $511.72$ | $852.87$ |
| **Lane 5** | $40.80$ | $42.00$ | $430.35$ | `430m` | $520.79$ | $867.98$ |
| **Lane 6** | $42.00$ | $43.20$ | $437.89$ | `438m` | $529.84$ | $883.08$ |
| **Lane 7** | $43.20$ | $44.40$ | $445.43$ | `445m` | $538.93$ | $898.18$ |
| **Lane 8** | $44.40$ | $45.60$ | $452.97$ | `453m` | $547.96$ | $913.29$ |
| **Total / Range** | $36.00 \to 44.40$ | $37.20 \to 45.60$ | $400.19 \to 452.97$ | `Lane 1`–`Lane 8` | **$4,130.04\text{ m}^2$** | $6,883.39\text{ m}$ |

### 2.2 Sub-Pixel Planimetric Digitization on Gaofen-2 (GF-2) Satellite Orthophoto

Using a pan-sharpened **Gaofen-2 (`GF-2`)** high-resolution satellite orthophoto (`Campus_GF2_Orthophoto.tif`, $2281 \times 1806\text{ pixels}$, 4-band 32-bit multispectral $B, G, R, \text{NIR}$, ground sampling distance $\text{GSD} = 0.8429\text{ m/px}$, referenced to `CGCS2000_Transverse_Mercator`), pixel-level heads-up vector digitization was conducted to extract hydrographic basins, multi-story academic buildings, and arterial road centerlines.

![GF-2 Satellite Orthophoto Campus Digitization](/images/arcgis-gf2-campus-digitization.webp)
*Figure 2: Sub-pixel vector digitization overlaid on the 0.84m GSD Gaofen-2 (`GF-2`) campus orthophoto, illustrating digitized shoreline vertices for Jixia Lake ($19,211.84\text{ m}^2$), orthogonal footprints for Yifu Library and Academic Buildings #12/#13 ($21,185.03\text{ m}^2$), and road centerlines ($2,021.81\text{ m}$).*

| Feature Class (Layer Name) | Geometry Type | Target Feature Name | Floor Count (`Floors`) | Planimetric Metric (`Area` / `Length`) | Engineering Digitization Specification |
| :--- | :--- | :--- | :---: | :---: | :--- |
| `Water_Body_Polygon` | Polygon | **Jixia Lake (Main Basin)** | — | $18,681.39\text{ m}^2$ | Sub-pixel shoreline tracing along water-vegetation spectral boundary |
| `Water_Body_Polygon` | Polygon | **Jixia Lake (North Basin)** | — | $530.46\text{ m}^2$ | Secondary northern pond separated by pedestrian causeway |
| `Building_Footprint_Polygon` | Polygon | **Yifu Library** | $4\text{ Floors}$ | $9,467.80\text{ m}^2$ | Crescent-shaped central library complex with curved southern facade |
| `Building_Footprint_Polygon` | Polygon | **Academic Building #12** | $5\text{ Floors}$ | $5,790.10\text{ m}^2$ | Southern E-shaped multi-wing instructional building |
| `Building_Footprint_Polygon` | Polygon | **Academic Building #13** | $5\text{ Floors}$ | $5,927.13\text{ m}^2$ | Northern E-shaped multi-wing instructional building |
| `Campus_Road_Centerline` | Polyline | **Qingnian Road** | — | $1,514.51\text{ m}$ | Primary east-west campus arterial corridor |
| `Campus_Road_Centerline` | Polyline | **Zhixing Road** | — | $507.31\text{ m}$ | Primary north-south western instructional corridor |

To format multi-line stacked cartographic labels combining feature names with planimetric metrics (`Area` in $\text{m}^2$ or `Length` in $\text{m}$) directly from the attribute tables, the following ArcGIS VBScript label expression is applied:

```vbscript
Function FindLabel([NAME], [AREA], [FLOORS])
  FindLabel = "<FNT size='10'><BOL>" & [NAME] & "</BOL></FNT>" & vbNewLine & _
              "Area: " & Round(CDbl([AREA]), 2) & " sq.m (" & [FLOORS] & "F)"
End Function
```

### 2.3 Coordinate-Rank Constrained Geodatabase Topological Validation & Zone-D Repair

Raw CAD-imported urban vector datasets frequently suffer from polygon self-overlaps, road-building boundary encroachments, and centerline-casing misalignments. To enforce strict spatial integrity across **Zone D** without corrupting survey-grade building footprints, the raw shapefiles (`Building_Polygon`: $95\text{ polygons}$, `Road_Polygon`: $83\text{ polygons}$, and `Road_Centerline`: $266\text{ polylines}$) were migrated into an Enterprise/File Geodatabase Feature Dataset (`Topology_Dataset`, `Beijing_1954_3_Degree_GK_CM_117E`, EPSG:2436) governed by a $0.001\text{ m}$ cluster tolerance ($\tau\_{xy} = 1\text{ mm}$).

<pre class="mermaid">
flowchart TD
    A["Ingest Raw CAD/Shapefile Layers into File Geodatabase Feature Dataset (EPSG:2436)"] --> B["Assign Coordinate Accuracy Ranks: Building_Polygon (XYRank = 1) vs. Road_Polygon &amp; Road_Centerline (XYRank = 2)"]
    B --> C["Configure 4 Geodatabase Topology Rules (Cluster Tolerance = 0.001 m)"]
    C --> D["Execute Full-Extent Topology Validation &amp; Isolate Zone-D Error Inspector Records"]
    D --> E{"Classify Topological Violation Type"}
    E -->|"Rule 1 &amp; 2: Area No Overlap"| F["Road_Polygon / Building_Polygon Self-Overlaps: Execute Merge or Subtract Redundant Slivers"]
    E -->|"Rule 3: Line Inside Area"| G["Road_Centerline Exceeding Road_Polygon Casing: Trim Dangles &amp; Snap Vertices Inside Road Casing"]
    E -->|"Rule 4: Area No Overlap With"| H["Road_Polygon Encroaching Building_Polygon: Execute Subtract Removing Road Overlap (Preserving Rank-1 Building Geometry)"]
    F --> I["Re-Validate Dirty Areas (T_1_DirtyAreas) Until Zero Unresolved Errors Remain in Zone D"]
    G --> I
    H --> I
</pre>

By assigning **`XYRank = 1`** to `Building_Polygon` (`DSID = 4`) and **`XYRank = 2`** to both `Road_Polygon` (`DSID = 5`) and `Road_Centerline` (`DSID = 6`), the Geodatabase topology engine guarantees that building vertices remain strictly anchored during automated cluster snapping, while road casing polygons yield to building boundaries during `Subtract` conflict resolution:

| Rule ID | ArcGIS Internal Rule Type | Origin Feature Class | Destination Feature Class | Coordinate Rank Hierarchy | Zone-D Engineering Remediation Action |
| :---: | :--- | :--- | :--- | :---: | :--- |
| `Rule 1` | `esriTRTAreaNoOverlap` (`Must Not Overlap`) | `Road_Polygon` (`DSID=5`) | `Road_Polygon` (`DSID=5`) | `XYRank = 2` | `Merge` or `Subtract` overlapping road intersection polygons |
| `Rule 2` | `esriTRTAreaNoOverlap` (`Must Not Overlap`) | `Building_Polygon` (`DSID=4`) | `Building_Polygon` (`DSID=4`) | `XYRank = 1` | Verify zero adjacent building footprint overlaps |
| `Rule 3` | `esriTRTLineInsideArea` (`Must Be Inside`) | `Road_Centerline` (`DSID=6`) | `Road_Polygon` (`DSID=5`) | `XYRank = 2` $\to$ `2` | Snap and trim protruding road centerline segments inside road polygons |
| `Rule 4` | `esriTRTAreaNoOverlapArea` (`Must Not Overlap With`) | `Road_Polygon` (`DSID=5`) | `Building_Polygon` (`DSID=4`) | `XYRank = 2` vs. **`XYRank = 1`** | Execute **`Subtract`** on `Road_Polygon` so `Building_Polygon` remains $100\%$ unmodified |

---

## 3. Multi-Criteria Spatial Boolean Site Selection & Graph-Theoretic Network Modeling

### 3.1 Euclidean Buffer Generation & Spatial Boolean Algebra for Commercial Site Selection

In urban retail planning, selecting an optimal land parcel for a new commercial complex requires simultaneously satisfying multiple positive accessibility criteria (proximity to arterial roads, financial institutions, and public transit stops) while enforcing a strict competitive exclusion zone around existing commercial malls.

Let the planar Euclidean distance between any point $p = (x, y) \in \mathbb{R}^2$ and a spatial feature set $F$ (points or polylines) be $d\_E(p, F) = \min\_{q \in F} \sqrt{(x - x\_q)^2 + (y - y\_q)^2}$. The uniform Euclidean buffer operator $B\_{F, r}$ of radius $r > 0$ generates the closed Minkowski sum of $F$ with a disk of radius $r$:

$$B\_{F, r} = \left\lbrace p \in \mathbb{R}^2 \ \middle|\ \min\_{q \in F} \left\|p - q\right\|\_2 \le r \right\rbrace$$

Given the four engineering siting criteria in `Beijing_1954_3_Degree_GK_CM_117E` (EPSG:2436):
1. **Main Arterial Corridor Proximity ($B\_{\text{road},100}$)**: Within $r\_1 = 100\text{ m}$ of the primary east-west arterial centerline (`Main_Arterial_Buffer_100m`).
2. **Financial Node Proximity ($B\_{\text{bank},150}$)**: Within $r\_2 = 150\text{ m}$ of $5$ commercial bank branches (`Bank_Buffer_150m`).
3. **Public Transit Accessibility ($B\_{\text{bus},50}$)**: Within $r\_3 = 50\text{ m}$ of $4$ bus transit stations (`Transit_Stop_Buffer_50m`).
4. **Competitive Market Exclusion ($B\_{\text{mall},300}$)**: Strictly outside ($d\_E > 300\text{ m}$) the $r\_4 = 300\text{ m}$ service buffer of $5$ existing shopping malls (`Existing_Mall_Buffer_300m`).

The feasible candidate parcel $S\_{\text{optimal}}$ is governed by the spatial Boolean algebra expression combining three-way set intersection ($\cap$, ArcGIS `Intersect`) with set difference ($\setminus$, ArcGIS `Erase`):

$$S\_{\text{optimal}} = \left(B\_{\text{road},100} \cap B\_{\text{bank},150} \cap B\_{\text{bus},50}\right) \setminus B\_{\text{mall},300}$$

<pre class="mermaid">
flowchart LR
    R["East-West Arterial Centerline"] -->|"Buffer (r = 100 m, Dissolve = ALL)"| BR["B_road,100 (282,314.89 m²)"]
    K["Commercial Banks (5 Points)"] -->|"Buffer (r = 150 m, Dissolve = ALL)"| BK["B_bank,150 (284,499.32 m²)"]
    T["Transit Stations (4 Points)"] -->|"Buffer (r = 50 m, Dissolve = NONE)"| BT["B_bus,50 (4 Polygons, 31,333.31 m²)"]
    M["Existing Malls (5 Points)"] -->|"Buffer (r = 300 m, Dissolve = ALL)"| BM["B_mall,300 Exclusion Zone (1,144,193.04 m²)"]
    BR --> INT["Spatial Intersect (B_road,100 ∩ B_bank,150 ∩ B_bus,50)"]
    BK --> INT
    BT --> INT
    INT -->|"3 Inclusion Polygons"| ERASE["Spatial Erase ( \\ B_mall,300 )"]
    BM -->|"Erase Features"| ERASE
    ERASE --> OPT["Optimal Mall Site Parcel S_optimal (ORIG_FID = 1, Area = 7,620.08 m²)"]
</pre>

Executing the three-way inclusion intersection $(B\_{\text{road},100} \cap B\_{\text{bank},150} \cap B\_{\text{bus},50})$ initially isolates $3$ candidate transit-oriented zones (`ORIG_FID IN (0, 1, 3)`). Subsequent application of the `Erase` operator against $B\_{\text{mall},300}$ completely eliminates the two western candidate zones (`ORIG_FID = 0` and `ORIG_FID = 3`, which fall deep inside the $300\text{ m}$ competitive radius of existing western malls), leaving the single optimal eastern parcel centered on **Transit Station #1 (`ORIG_FID = 1`)** with an exact usable land area of **$7,620.08\text{ m}^2$** and perimeter of **$343.86\text{ m}$**.

![Multi-Criteria Commercial Mall Site Selection](/images/arcgis-mall-site-selection.webp)
*Figure 3: Multi-Criteria Spatial Decision Support System (MC-SDSS) overlay in EPSG:2436, showing the four standard Euclidean buffer zones (`B_road,100`, `B_bank,150`, `B_bus,50`, `B_mall,300`) and the final Boolean-clipped candidate site $S\_{\text{optimal}} = 7,620.08\text{ m}^2$.*

| Spatial Layer / Geoprocessing Stage | Buffer Radius ($r$) | Boolean Role | Feature Count | Total Planar Area ($\text{m}^2$) | Boundary Perimeter ($\text{m}$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `Main_Arterial_Buffer_100m` ($B\_{\text{road},100}$) | $100.0\text{ m}$ | Inclusion ($\cap$) | $1\text{ (Dissolved)}$ | $282,314.89$ | $3,137.65$ |
| `Bank_Buffer_150m` ($B\_{\text{bank},150}$) | $150.0\text{ m}$ | Inclusion ($\cap$) | $1\text{ (Dissolved)}$ | $284,499.32$ | $3,177.02$ |
| `Transit_Stop_Buffer_50m` ($B\_{\text{bus},50}$) | $50.0\text{ m}$ | Inclusion ($\cap$) | $4\text{ (Individual)}$ | $31,333.31$ | $1,255.81$ |
| `Existing_Mall_Buffer_300m` ($B\_{\text{mall},300}$) | $300.0\text{ m}$ | Exclusion ($\setminus$) | $1\text{ (Dissolved)}$ | $1,144,193.04$ | $5,811.53$ |
| `Optimal_Mall_Site_Parcel` ($S\_{\text{optimal}}$) | — | **Final Output** | **$1\text{ (`ORIG_FID = 1`)}$** | **$7,620.08$** | **$343.86$** |

### 3.2 Graph-Theoretic Road Network Accessibility (`Dijkstra`) & Planar Voronoi (`Thiessen`) Partitioning

While Euclidean buffers model isotropic straight-line distance, real-world urban movement is constrained to topological road networks. Conversely, macro-scale regional service catchment partitioning across discrete hub locations is governed by planar Voronoi tessellation.

#### 1. Topological Network Graph & Dijkstra Shortest-Path Optimization

In ArcGIS Network Analyst, the urban road centerline layer (`Road_Centerline`, $|E| = 266\text{ edges}$) and topological junction layer (`Road_Centerline_ND_Junctions`, $|V| = 231\text{ nodes}$) form a weighted planar graph $G = (V, E, W)$, where edge weight $w(e) = \ell(e) > 0$ represents metric segment length. Given an origin node $u \in V$ and destination node $v \in V$, **Dijkstra's algorithm** computes the minimum-impedance path $\pi^{\ast}(u, v)$ by iteratively relaxing tentative labels $D(v) = \min\_{u \in N(v)} \left[D(u) + w(u, v)\right]$:

$$d\_G(u, v) = \min\_{\pi \in \Pi(u, v)} \sum\_{e \in \pi} w(e)$$

Building upon the network metric $d\_G(\cdot, \cdot)$, three operational network analyses were executed:
* **Point-to-Point Shortest Path Routing**: Minimizing cumulative edge impedance across the campus logistics network yields a cross-campus optimal delivery route of **$980.1\text{ m}$**.
* **Multi-Threshold Network Service Area ($\mathcal{A}(F, \tau)$)**: Given a set of service centers $F$ ($5$ dining facilities), the network service area at impedance cutoff $\tau$ (e.g., Tier 1 $\tau\_1 = 180\text{ m}$, Tier 2 $\tau\_2 = 360\text{ m}$) is the subgraph of all reachable network locations:
  $$\mathcal{A}(F, \tau) = \left\lbrace x \in G \ \middle|\ \min\_{f \in F} d\_G(f, x) \le \tau \right\rbrace$$
* **Closest Facility Allocation ($f^{\ast}(p\_k)$)**: For each demand/incident location $p\_k \in \lbrace p\_1, p\_2, p\_3\rbrace$, the solver evaluates $f^{\ast}(p\_k) = \underset{f \in F}{\arg\min}\ d\_G(p\_k, f)$, establishing minimum-impedance response routes of **$72.8\text{ m}$** (Incident #1), **$886.6\text{ m}$** (Incident #2), and **$896.3\text{ m}$** (Incident #3).

#### 2. Planar Voronoi Tessellation (Thiessen Polygons)

Given a set of $n = 34$ distinct generator seed points $P = \lbrace p\_1, p\_2, \dots, p\_{34}\rbrace \subset \mathbb{R}^2$ (`Provincial_Capital_Hubs`), the **Voronoi diagram (Thiessen polygon tessellation)** partitions the plane into $n$ convex dominance regions $V(p\_i)$ such that every location $x \in V(p\_i)$ is closer to generator $p\_i$ than to any other generator $p\_j$ ($j \ne i$):

$$V\left(p\_i\right) = \left\lbrace x \in \mathbb{R}^2 \ \middle|\ \left\|x - p\_i\right\|\_2 \le \left\|x - p\_j\right\|\_2, \quad \forall j \ne i \right\rbrace = \bigcap\_{j \ne i} H\left(p\_i, p\_j\right)$$

Where $H(p\_i, p\_j) = \left\lbrace x \in \mathbb{R}^2 \mid (x - \frac{p\_i + p\_j}{2}) \cdot (p\_j - p\_i) \le 0 \right\rbrace$ is the closed half-plane bounded by the perpendicular bisector of segment $\overline{p\_i p\_j}$. Geometrically, the Voronoi tessellation $\mathcal{V}(P)$ is the exact planar dual of the **Delaunay triangulation** $\mathcal{D}(P)$: every Voronoi vertex sits at the circumcenter of a Delaunay triangle whose circumcircle contains no other generator points in its interior.

![Road Network Accessibility & Voronoi Partitioning](/images/arcgis-network-thiessen-analysis.webp)
*Figure 4: Dual-scale accessibility modeling in ArcGIS: (A) Graph-theoretic road network analysis (`266 edges`, `231 junctions`, EPSG:2436) showing multi-tier service zones, cross-network shortest routing ($980.1\text{ m}$), and closest-facility allocation for Incidents #1–#3; (B) Planar Voronoi tessellation (`Voronoi_Service_Polygons`, $34\text{ cells}$) partitioning national influence zones across 34 provincial capital hubs.*

### 3.3 3D Terrain-Drape Extrusion & Keyframe Flythrough Modeling in ArcScene

To extend 2D planimetric vector layers into a 3D urban digital twin environment (`ArcScene`), two-dimensional building footprints (`Building_Polygon`, $95\text{ polygons}$), hydrographic features (`Water_System_Polygon`, $11\text{ polygons}$), and road casings (`Road_Polygon`, $83\text{ polygons}$) are draped over a Triangulated Irregular Network / raster elevation surface (`Terrain_Surface_DEM`):

1. **Base Height Draping ($Z\_{\text{base}}$)**: Every 2D vertex $(x\_i, y\_i)$ inherits its ground elevation $Z\_{\text{base}}(x\_i, y\_i)$ via bilinear interpolation from the underlying digital elevation surface.
2. **Attribute-Driven 3D Solid Extrusion ($Z\_{\text{top}}$)**: Building polygons are extruded vertically into 3D prismatic solids by mapping the structural height attribute `[height]` ($\Delta H\_k$) to the extrusion expression:
   $$Z\_{\text{top}}(x, y) = Z\_{\text{base}}(x, y) + \Delta H\_k$$
3. **Keyframe Camera Trajectory Interpolation**: By capturing sequential 6-DoF camera keyframes $\mathbf{K}\_m = (X\_c, Y\_c, Z\_c, \text{Azimuth}, \text{Inclination}, \text{Roll})\_m$ along a closed spline path and interpolating over a $>15\text{ s}$ timeline, the scene engine renders a smooth 3D aerial flythrough across the extruded architectural complex.

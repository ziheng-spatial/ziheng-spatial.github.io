---
title: "Zero-Dependency Stereo Image Matching Engine via Normalized Cross-Correlation (ZNCC) in Native C++"
date: 2026-11-08
draft: false
math: true
tags: ["C++", "Photogrammetry", "Stereo Vision", "Image Matching", "ZNCC", "Binary BMP Parsing"]
categories: ["Photogrammetry & Remote Sensing"]
summary: "From-scratch C/C++ stereo homologous point matching engine featuring raw binary BMP parsing with 4-byte row padding alignment, dynamic 2D heap matrix management, single-pass Zero-Mean Normalized Cross-Correlation (ZNCC) sliding-window evaluation across 2,754 candidate windows, and pixel-level crosshair overlay rendering."
---

## 1. Engineering Specifications & Experimental Benchmark

In digital photogrammetry and computational stereo vision, establishing high-precision homologous point correspondences (conjugate image points) across overlapping aerial stereo pairs is the foundational prerequisite for relative orientation, epipolar rectification, and 3D digital elevation model (DEM) generation.

This project implements a **zero-dependency native C/C++ stereo image matching engine** (`Exp02_ImageMatching`) built entirely from scratch using only `<stdio.h>` and `<math.h>`—deliberately bypassing high-level computer vision frameworks such as OpenCV to expose the low-level mechanics of binary raster stream parsing, 4-byte scanline memory alignment, dynamic 2D matrix allocation, and single-pass **Zero-Mean Normalized Cross-Correlation (ZNCC / NCC)** evaluation.

| Pipeline Stage / Metric | Experimental Specification | Engineering Telemetry & Remarks |
| :--- | :--- | :--- |
| **Core Language & Build Standard** | Native C/C++ (ISO C++20 / CMake 4.0) | Zero third-party image/math library dependencies (`<stdio.h>`, `<math.h>`) |
| **Step 1: Stereo Input Imagery** | $1024 \times 1024\text{ px}$ (`left.bmp`, `right.bmp`) | 8-bit grayscale intensity range $[0, 255]$; Bottom-Up binary BMP layout |
| **Step 2: Template Window ($v \times w$)** | $11 \times 11\text{ px}$ ($N = 121\text{ pixels}$) | Half-window radius $\Delta v = \Delta w = 5\text{ px}$ around target center |
| **Step 3: Left Target Feature Point** | $\text{Row }(y\_L) = 909,\quad \text{Col }(x\_L) = 428$ | Center pixel intensity $g(909, 428) = 162.0$; high-gradient road-plaza corner |
| **Step 4: Predicted Right Search Zone** | $\text{Row } [899 \sim 949],\quad \text{Col } [5 \sim 58]$ | Clamped to left border guard ($c\_{\min} = \Delta w = 5$); **$51 \times 54 = 2,754$** candidate windows |
| **Step 5: Correlation Storage Matrix** | $51 \times 54$ (`double** corrMatrix`) | Evaluates $2,754 \times 121 = 333,234$ pixel-pair inner products in a single pass |
| **Step 6: Matched Conjugate Point** | $\text{Row }(y\_R^{\ast}) = 930,\quad \text{Col }(x\_R^{\ast}) = 18$ | Global maximum peak across the $51 \times 54$ correlation surface |
| **Step 6: Stereo Parallax $(\Delta r, \Delta c)$** | $(\Delta\text{Row} = +21,\quad \Delta\text{Col} = -410)\text{ px}$ | $\Delta r = 930 - 909 = +21\text{ px}$; $\Delta c = 18 - 428 = -410\text{ px}$ |
| **Step 6: Peak Correlation ($r\_{\max}$)** | **$0.982561$** | High radiometric invariance and sharp unimodal correlation peak ($r\_{\max} \to 1.0$) |

![CLion Terminal Execution Telemetry for Steps 1 to 6](/images/ncc-clion-execution.webp)
*Figure 1: Complete execution telemetry in JetBrains CLion executing Steps 1 through 6 on the $1024 \times 1024$ stereo pair, converging on conjugate point $(930, 18)$ with stereo parallax $(+21, -410)$ and peak correlation $r_{\max} = 0.982561$.*

---

## 2. Mathematical Formulation of ZNCC Stereo Matching

### 2.1 Continuous & Discrete Zero-Mean Normalized Cross-Correlation

Area-Based Matching (ABM) formulates conjugate point recognition as a statistical signal similarity problem between a reference template window $g(x, y)$ centered on the left image target point and a candidate sliding window $g^{\prime}(x^{\prime}, y^{\prime}) = g^{\prime}(x + p, y + q)$ shifted by disparity parameters $(p, q)$ in the right search image.

Statistically, the cross-correlation coefficient $r(p, q)$ is the standardized covariance between the two 2D luminance signals, normalized by the product of their respective standard deviations:

$$r(p, q) = \frac{\text{Cov}\left(g, g^{\prime}\right)}{\sqrt{\text{Var}(g) \cdot \text{Var}\left(g^{\prime}\right)}} = \frac{\sigma\_{gg^{\prime}}(p, q)}{\sigma\_g \cdot \sigma\_{g^{\prime}}(p, q)}$$

For discrete digital imagery over an odd-sized rectangular template window of $v \times w$ pixels (where $v = w = 11$, total window pixels $N = v \cdot w = 121$, and half-window radii $h\_v = \lfloor v/2 \rfloor = 5$, $h\_w = \lfloor w/2 \rfloor = 5$), the discrete **Zero-Mean Normalized Cross-Correlation (ZNCC)** estimator between left target center $(r\_L, c\_L)$ and right candidate center $(r\_R, c\_R)$ is defined as:

$$r\left(r\_L, c\_L; r\_R, c\_R\right) = \frac{\sum\_{i=-h\_v}^{h\_v} \sum\_{j=-h\_w}^{h\_w} \left(g\_{r\_L+i, c\_L+j} - \bar{g}\right)\left(g^{\prime}\_{r\_R+i, c\_R+j} - \bar{g}^{\prime}\right)}{\sqrt{\left[\sum\_{i=-h\_v}^{h\_v} \sum\_{j=-h\_w}^{h\_w} \left(g\_{r\_L+i, c\_L+j} - \bar{g}\right)^2\right] \cdot \left[\sum\_{i=-h\_v}^{h\_v} \sum\_{j=-h\_w}^{h\_w} \left(g^{\prime}\_{r\_R+i, c\_R+j} - \bar{g}^{\prime}\right)^2\right]}}$$

Where the local window sample means $\bar{g}$ and $\bar{g}^{\prime}$ are given by:

$$\bar{g} = \frac{1}{v \cdot w}\sum\_{i=-h\_v}^{h\_v} \sum\_{j=-h\_w}^{h\_w} g\_{r\_L+i, c\_L+j}, \qquad \bar{g}^{\prime} = \frac{1}{v \cdot w}\sum\_{i=-h\_v}^{h\_v} \sum\_{j=-h\_w}^{h\_w} g^{\prime}\_{r\_R+i, c\_R+j}$$

By explicitly subtracting the local mean ($\bar{g}, \bar{g}^{\prime}$) and dividing by the local standard deviation, ZNCC achieves complete invariance to linear radiometric distortions between stereo exposures. Specifically, under an affine illumination transform $g^{\prime} = \beta \cdot g + \alpha$ (where $\alpha$ models additive exposure offset and $\beta > 0$ models multiplicative contrast gain), $r(g, \beta g + \alpha) \equiv 1.0$.

### 2.2 Single-Pass Algebraic Expansion for High-Speed Sliding Windows

Evaluating the two-pass centered ZNCC formula directly requires two sequential loops over every $11 \times 11$ candidate window: a first pass to compute $\bar{g}$ and $\bar{g}^{\prime}$, and a second pass to accumulate the centered deviations. To cut memory bandwidth and loop overhead in half across thousands of candidate positions, we expand the covariance numerator and variance denominators algebraically:

$$\sum\_{i}\sum\_{j} \left(g\_{ij} - \bar{g}\right)\left(g^{\prime}\_{ij} - \bar{g}^{\prime}\right) = \sum\_{i}\sum\_{j} g\_{ij} g^{\prime}\_{ij} - \frac{1}{N}\left(\sum\_{i}\sum\_{j} g\_{ij}\right)\left(\sum\_{i}\sum\_{j} g^{\prime}\_{ij}\right)$$

$$\sum\_{i}\sum\_{j} \left(g\_{ij} - \bar{g}\right)^2 = \sum\_{i}\sum\_{j} g\_{ij}^2 - \frac{1}{N}\left(\sum\_{i}\sum\_{j} g\_{ij}\right)^2, \qquad \sum\_{i}\sum\_{j} \left(g^{\prime}\_{ij} - \bar{g}^{\prime}\right)^2 = \sum\_{i}\sum\_{j} \left(g^{\prime}\_{ij}\right)^2 - \frac{1}{N}\left(\sum\_{i}\sum\_{j} g^{\prime}\_{ij}\right)^2$$

Substituting these identities yields the **single-pass operational ZNCC formula** implemented in `calcCorrelation`:

$$r = \frac{\sum\sum g \cdot g^{\prime} - \frac{1}{vw}\left(\sum\sum g\right)\left(\sum\sum g^{\prime}\right)}{\sqrt{\left[\sum\sum g^2 - \frac{1}{vw}\left(\sum\sum g\right)^2\right] \cdot \left[\sum\sum \left(g^{\prime}\right)^2 - \frac{1}{vw}\left(\sum\sum g^{\prime}\right)^2\right]}}$$

Within a single traversal of the $11 \times 11$ neighborhood ($N = vw = 121$), five scalar accumulators—$\sum g$, $\sum g^2$, $\sum g^{\prime}$, $\sum \left(g^{\prime}\right)^2$, and $\sum (g \cdot g^{\prime})$—are updated simultaneously in CPU registers.

### 2.3 Search Space Complexity & Stereo Parallax Formulation

Given the target point $(r\_L, c\_L) = (909, 428)$ in the $1024 \times 1024$ left image, an unconstrained brute-force search across all valid $11 \times 11$ windows in the right image would require evaluating:

$$N\_{\text{brute}} = \left(H - 2h\_v\right) \times \left(W - 2h\_w\right) = (1024 - 10) \times (1024 - 10) = 1,014^2 = 1,028,196\text{ windows}$$

By incorporating prior aerial stereo overlap geometry (approximate along-track column parallax $\approx -400\text{ px}$ and cross-track row parallax $\approx +20\text{ px}$), the initial search interval is constrained to $[r\_L - 10, r\_L + 40] \times [c\_L - 430, c\_L - 370] = [899, 949] \times [-2, 58]$. Enforcing boundary clamping so that the $11 \times 11$ window never crosses the image edge ($c\_{\min} = \max(-2, h\_w) = 5$) yields the exact bounded search domain $\Omega\_S$:

$$\Omega\_S = \left\lbrace\left(r\_R, c\_R\right) \in \mathbb{Z}^2 \ \middle|\ 899 \le r\_R \le 949, \quad 5 \le c\_R \le 58\right\rbrace$$

$$N\_{\text{search}} = \left(r\_{\max} - r\_{\min} + 1\right) \times \left(c\_{\max} - c\_{\min} + 1\right) = 51 \times 54 = 2,754\text{ candidate windows}$$

This prior parallax constraint reduces computational complexity from $\mathcal{O}(H \cdot W \cdot v \cdot w)$ to $\mathcal{O}(S\_r \cdot S\_c \cdot v \cdot w)$, eliminating **$99.73\%$** of redundant window evaluations ($333,234$ pixel-pair operations vs. $1.244 \times 10^8$) while preventing false matches in repetitive agricultural textures. The optimal conjugate point $(r\_R^{\ast}, c\_R^{\ast})$ and stereo parallax vector $(\Delta r, \Delta c)$ are then obtained via argmax localization over the correlation matrix:

$$\left(r\_R^{\ast}, c\_R^{\ast}\right) = \underset{(r\_R, c\_R) \in \Omega\_S}{\arg\max}\ r\left(r\_L, c\_L; r\_R, c\_R\right) = (930, 18), \qquad r\_{\max} = 0.982561$$

$$\begin{cases} \Delta r = r\_R^{\ast} - r\_L = 930 - 909 = +21\text{ px} \\\\ \Delta c = c\_R^{\ast} - c\_L = 18 - 428 = -410\text{ px} \end{cases}$$

---

## 3. End-to-End Algorithmic Pipeline & Native C++ Architecture

<pre class="mermaid">
flowchart TD
    A["Binary BMP Stream Ingestion: left.bmp &amp; right.bmp (1024 x 1024)"] --> B["BMP Header Verification (0x424D) &amp; 4-Byte Row Padding Calculation"]
    B --> C["Bottom-Up to Top-Down Scanline Inversion &amp; Dynamic 2D Heap Allocation (gLeft, gRight)"]
    C --> D["Target Feature Selection: Left Image (Row = 909, Col = 428), Gray = 162.0, Window = 11x11"]
    D --> E["Prior Parallax Search Prediction &amp; Boundary Clamping: Row [899..949], Col [5..58] (2,754 Windows)"]
    E --> F["Sliding-Window Single-Pass ZNCC Evaluation &amp; 51x54 Correlation Matrix Construction"]
    F --> G["Global Peak Localization: r_max = 0.982561 at Right Conjugate Point (Row = 930, Col = 18)"]
    G --> H["Stereo Parallax Computation: Delta_Row = +21 px, Delta_Col = -410 px"]
    H --> I["In-Memory Binary BMP Overlay (markPointOnBmp): 31px Crosshair &amp; 11x11 Bounding Box"]
    I --> J["Export Annotated Imagery (left_matched.bmp, right_matched.bmp) &amp; Deallocate Heap Matrices"]
</pre>

### 3.1 Dynamic 2D Heap Matrix Management (`createMatrix` / `freeMatrix`)

Allocating two $1024 \times 1024$ double-precision luminance matrices ($8\text{ MB}$ each) on the call stack would immediately trigger a stack overflow on standard operating system threads. To maintain deterministic memory lifetimes without `std::vector` overhead, the engine manages 2D heap matrices (`createMatrix` / `allocMatrix` and `freeMatrix`) via explicit row-pointer arrays (`double**`):

```cpp
// Dynamic 2D double-precision matrix allocation (allocMatrix / createMatrix)
double** createMatrix(int rows, int cols) {
    double** mat = new double*[rows];
    for (int i = 0; i < rows; i++) {
        mat[i] = new double[cols];
        for (int j = 0; j < cols; j++) {
            mat[i][j] = 0.0;
        }
    }
    return mat;
}

// Deterministic row-by-row heap deallocation
void freeMatrix(double** mat, int rows) {
    if (mat == NULL) return;
    for (int i = 0; i < rows; i++) {
        delete[] mat[i];
    }
    delete[] mat;
}
```

### 3.2 Native Binary BMP Parsing & 4-Byte Row Padding Alignment (`readBmpGray`)

Uncompressed Windows Device-Independent Bitmaps (`BITMAPFILEHEADER` + `BITMAPINFOHEADER`) enforce two low-level binary layout rules that must be handled explicitly when reading raw byte streams via `fread` and `fseek`:

1. **4-Byte Scanline Row Padding**: The BMP specification mandates that the byte stride of every horizontal scanline (`lineBytes`) must be an integer multiple of $4\text{ bytes}$ ($32\text{ bits}$). If `width * byteCount` is not divisible by $4$, up to $3$ padding bytes are appended to the end of each row on disk. The exact padded row stride is computed via integer ceiling arithmetic:
   $$\text{lineBytes} = \left\lfloor \frac{\text{width} \times \text{byteCount} + 3}{4} \right\rfloor \times 4$$
2. **Bottom-Up Scanline Orientation**: When the header `height` field is positive ($H > 0$), BMP scanlines are stored in **Bottom-Up** order—meaning the first scanline at `dataOffset` corresponds to the bottom row ($r = H - 1$) of the image. The parser inverts the row index via `int r = (height > 0) ? (realHeight - 1 - i) : i` to populate a standard Top-Down photogrammetric row-column matrix, while supporting both single-channel 8-bit grayscale (`byteCount == 1`) and 24-bit BGR (`byteCount >= 3`) mapped to 8-bit luminance via ITU-R BT.601 weights ($0.299R + 0.587G + 0.114B$):

```cpp
// Native binary BMP parser with 4-byte row padding alignment & Bottom-Up inversion
int readBmpGray(FILE* fp, double** &grayMat, int &width, int &height) {
    unsigned char magic[2] = {0};
    fread(magic, 1, 2, fp);
    if (magic[0] != 0x42 || magic[1] != 0x4D) {
        printf("Invalid BMP signature!\n");
        return FAILURE;
    }

    int dataOffset = 0;
    unsigned short bitCount = 0;

    fseek(fp, 10, SEEK_SET);
    fread(&dataOffset, sizeof(int), 1, fp);

    fseek(fp, 18, SEEK_SET);
    fread(&width, sizeof(int), 1, fp);
    fread(&height, sizeof(int), 1, fp);

    fseek(fp, 28, SEEK_SET);
    fread(&bitCount, sizeof(unsigned short), 1, fp);

    int realHeight = myAbs(height);
    int byteCount = bitCount / 8;
    int lineBytes = (width * byteCount + 3) / 4 * 4; // 4-byte scanline alignment

    grayMat = createMatrix(realHeight, width);
    unsigned char* rowBuf = new unsigned char[lineBytes];

    fseek(fp, dataOffset, SEEK_SET);
    for (int i = 0; i < realHeight; i++) {
        int r = (height > 0) ? (realHeight - 1 - i) : i; // Bottom-Up to Top-Down flip
        fread(rowBuf, 1, lineBytes, fp);

        for (int c = 0; c < width; c++) {
            if (byteCount == 1) {
                grayMat[r][c] = (double)rowBuf[c];
            } else if (byteCount >= 3) {
                unsigned char B = rowBuf[c * byteCount + 0];
                unsigned char G = rowBuf[c * byteCount + 1];
                unsigned char R = rowBuf[c * byteCount + 2];
                grayMat[r][c] = 0.299 * R + 0.587 * G + 0.114 * B;
            }
        }
    }

    height = realHeight;
    delete[] rowBuf;
    return SUCCESS;
}
```

### 3.3 Single-Pass ZNCC Kernel & Sliding-Window Evaluation (`calcCorrelation`)

For each of the $2,754$ candidate centers $(r\_R, c\_R) \in [899, 949] \times [5, 58]$, `calcCorrelation` executes the single-pass operational formula over the $11 \times 11$ window (`v = 11, w = 11`), guarded against zero-variance homogeneous patches (`varG <= 0.0 || varGP <= 0.0`):

```cpp
// Step 5: Single-pass operational ZNCC correlation kernel
double calcCorrelation(double** gLeft, double** gRight, int rowL, int colL, int rowR, int colR, int v, int w) {
    int halfV = v / 2;
    int halfW = w / 2;
    double N = (double)(v * w);

    double sumG   = 0.0; // Sum of g
    double sumG2  = 0.0; // Sum of g^2
    double sumGP  = 0.0; // Sum of g'
    double sumGP2 = 0.0; // Sum of g'^2
    double sumGGP = 0.0; // Cross-product sum of (g * g')

    for (int i = -halfV; i <= halfV; i++) {
        for (int j = -halfW; j <= halfW; j++) {
            double g  = gLeft[rowL + i][colL + j];
            double gp = gRight[rowR + i][colR + j];

            sumG   += g;
            sumG2  += g * g;
            sumGP  += gp;
            sumGP2 += gp * gp;
            sumGGP += g * gp;
        }
    }

    double numerator = sumGGP - (sumG * sumGP) / N;
    double varG  = sumG2  - (sumG * sumG) / N;
    double varGP = sumGP2 - (sumGP * sumGP) / N;

    if (varG <= 0.0 || varGP <= 0.0) {
        return 0.0;
    }
    return numerator / sqrt(varG * varGP);
}
```

### 3.4 Pixel-Level Crosshair & Template Box Rendering (`markPointOnBmp`)

Once the global correlation peak $r\_{\max} = 0.982561$ is locked at $(930, 18)$, `markPointOnBmp` loads the raw binary BMP buffer into memory and directly rasterizes a $31\text{ px}$ crosshair (`dr == 0 || dc == 0` over $[-15, +15]$) combined with the $11 \times 11$ template window perimeter (`myAbs(dr) == halfWin || myAbs(dc) == halfWin`) by mapping top-down coordinates $(r, c)$ back into Bottom-Up byte offsets `pos = dataOffset + bmpRow * lineBytes + c * byteCount`:

```cpp
// Step 6 Helper: In-place binary BMP rasterization of 31px crosshair and 11x11 window box
int markPointOnBmp(const char* srcPath, const char* dstPath, int markRow, int markCol, int winSize) {
    FILE* fpIn = fopen(srcPath, "rb");
    if (fpIn == NULL) return FAILURE;

    fseek(fpIn, 0, SEEK_END);
    long fileSize = ftell(fpIn);
    fseek(fpIn, 0, SEEK_SET);

    unsigned char* fileBuf = new unsigned char[fileSize];
    fread(fileBuf, 1, fileSize, fpIn);
    fclose(fpIn);

    int dataOffset = *(int*)(fileBuf + 10);
    int width      = *(int*)(fileBuf + 18);
    int height     = *(int*)(fileBuf + 22);
    unsigned short bitCount = *(unsigned short*)(fileBuf + 28);

    int realHeight = myAbs(height);
    int byteCount = bitCount / 8;
    int lineBytes = (width * byteCount + 3) / 4 * 4;
    int halfWin = winSize / 2;

    // Rasterize 31px crosshair (radius 15) and 11x11 template window perimeter
    for (int dr = -15; dr <= 15; dr++) {
        for (int dc = -15; dc <= 15; dc++) {
            bool isCross = (dr == 0 || dc == 0);
            bool isBox   = ((myAbs(dr) == halfWin && myAbs(dc) <= halfWin) ||
                            (myAbs(dc) == halfWin && myAbs(dr) <= halfWin));

            if (isCross || isBox) {
                int r = markRow + dr;
                int c = markCol + dc;
                if (r >= 0 && r < realHeight && c >= 0 && c < width) {
                    int bmpRow = (height > 0) ? (realHeight - 1 - r) : r;
                    int pos = dataOffset + bmpRow * lineBytes + c * byteCount;
                    if (byteCount == 1) {
                        fileBuf[pos] = 255; // Pure white marker for 8-bit single-channel
                    } else if (byteCount >= 3) {
                        fileBuf[pos + 0] = 0;   // B
                        fileBuf[pos + 1] = 0;   // G
                        fileBuf[pos + 2] = 255; // R (High-contrast red marker)
                    }
                }
            }
        }
    }

    FILE* fpOut = fopen(dstPath, "wb");
    if (fpOut == NULL) {
        delete[] fileBuf;
        return FAILURE;
    }
    fwrite(fileBuf, 1, fileSize, fpOut);
    fclose(fpOut);

    delete[] fileBuf;
    return SUCCESS;
}
```

---

## 4. Visual Verification & Photogrammetric Analysis

The annotated output stereo pair (`left_matched.bmp` and `right_matched.bmp`) is presented in Figures 2 and 3 below.

![Left Aerial Image Target Feature Point (909, 428) with 11x11 Template Window](/images/ncc-left-matched.webp)
*Figure 2: Left reference aerial image (`left_matched.bmp`, $1024 \times 1024$) showing the selected target feature point at $(\text{Row} = 909, \text{Col} = 428)$ with center intensity $162.0$, marked by a red $31\text{ px}$ crosshair and $11 \times 11$ template window along the northwestern rim of the circular plaza near the lower road bend.*

![Right Aerial Image Matched Conjugate Point (930, 18) Located via ZNCC](/images/ncc-right-matched.webp)
*Figure 3: Right search aerial image (`right_matched.bmp`, $1024 \times 1024$) illustrating the automatically matched conjugate point at $(\text{Row} = 930, \text{Col} = 18)$ located across $2,754$ candidate windows with peak correlation $r_{\max} = 0.982561$.*

### 4.1 Photogrammetric Precision & Edge-Guard Diagnostics

1. **Unimodal Correlation Peak ($r\_{\max} = 0.982561$)**: The achieved correlation coefficient of $0.982561$ substantially exceeds standard operational photogrammetric acceptance thresholds ($r \ge 0.80$). Because the target point at $(909, 428)$ sits at the high-contrast geometric junction between the curved road and circular rotunda structure, the $11 \times 11$ template captures orthogonal intensity gradients in both row and column directions, eliminating aperture ambiguity.
2. **Epipolar & Overlap Parallax Geometry**: The recovered disparity vector $(\Delta r = +21\text{ px}, \Delta c = -410\text{ px})$ directly reflects the physical flight geometry of the stereo strip. The large horizontal shift ($\Delta c = -410\text{ px}$ across a $1024\text{ px}$ frame, corresponding to $\approx 60\%$ forward overlap) represents the primary along-track base-to-height ($B/H$) parallax, whereas the minor vertical offset ($\Delta r = +21\text{ px}$) captures residual crab angle ($\kappa$) and attitude perturbation between consecutive exposures.
3. **Near-Border Window Guard Validation**: Because the conjugate point in the right image lies at column $x\_R^{\ast} = 18\text{ px}$—only $18\text{ pixels}$ away from the left image boundary—an unguarded search range of $[428 - 430, 428 - 370] = [-2, 58]$ would have accessed negative column indices (`colR + j < 0`) during the $11 \times 11$ window convolution. Clamping `searchColMin` to `halfW = 5` guarantees safe memory bounds while preserving the complete $51 \times 54$ ($2,754$-window) correlation surface around $(930, 18)$.

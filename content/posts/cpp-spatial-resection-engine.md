+++
date = '2026-10-06T18:03:41+08:00'
draft = false
title = 'Cpp Spatial Resection Engine'
+++

### Overview
A high-precision single-photo spatial resection engine implemented in pure C++ for rigorous photogrammetric measurement, featuring collinearity equation linearization and iterative least-squares adjustment.

### Core Features
- Rigorous mathematical modeling based on collinearity equations.
- Automated iteration with convergence criteria checking.
- Precision evaluation via root mean square error (RMSE).

### Source Code

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>

using namespace std;

// 像点与地面控制点坐标结构体
struct Point {
    double x, y;
    double X, Y, Z;
};

// 矩阵转置
vector<vector<double>> Transpose(const vector<vector<double>>& A) {
    int m = A.size();
    int n = A[0].size();
    vector<vector<double>> AT(n, vector<double>(m, 0.0));
    for (int i = 0; i < m; i++)
        for (int j = 0; j < n; j++)
            AT[j][i] = A[i][j];
    return AT;
}

// 矩阵乘法
vector<vector<double>> Multiply(const vector<vector<double>>& A, const vector<vector<double>>& B) {
    int m = A.size();
    int n = A[0].size();
    int p = B[0].size();
    vector<vector<double>> AB(m, vector<double>(p, 0.0));
    for (int i = 0; i < m; i++)
        for (int j = 0; j < p; j++)
            for (int k = 0; k < n; k++)
                AB[i][j] += A[i][k] * B[k][j];
    return AB;
}

// 矩阵求逆
vector<vector<double>> Inverse(vector<vector<double>> A) {
    int n = A.size();
    vector<vector<double>> E(n, vector<double>(n, 0.0));
    for (int i = 0; i < n; i++) E[i][i] = 1.0;

    for (int i = 0; i < n; i++) {
        double mainElement = A[i][i];
        for (int j = 0; j < n; j++) {
            A[i][j] /= mainElement;
            E[i][j] /= mainElement;
        }
        for (int j = 0; j < n; j++) {
            if (i != j) {
                double factor = A[j][i];
                for (int k = 0; k < n; k++) {
                    A[j][k] -= factor * A[i][k];
                    E[j][k] -= factor * E[i][k];
                }
            }
        }
    }
    return E;
}

int main() {
    // 1. 输入完整的单像空间后方交会已知数据
    vector<Point> pts = {
            {-86.15, -68.99, 36589.41, 25273.32, 2195.17},
            {-53.40,  82.21, 37631.08, 31324.51,  728.69},
            {-14.78, -76.63, 39100.97, 24934.98, 2386.50},
            { 10.46,  64.43, 40426.54, 30319.81,  757.31}
    };

    int n = pts.size();
    double f = 153.24;
    double m_scale = 40000.0;
    double x0 = 0.0, y0 = 0.0;

    // 2. 确定外方位元素初始值
    double Xs = 0, Ys = 0, Z_avg = 0;
    for (int i = 0; i < n; i++) {
        Xs += pts[i].X;
        Ys += pts[i].Y;
        Z_avg += pts[i].Z;
    }
    Xs /= n;
    Ys /= n;
    Z_avg /= n;

    double Zs = Z_avg + m_scale * f / 1000.0;
    double phi = 0.0, omega = 0.0, kappa = 0.0;

    double limit = 0.00001;
    int iteration = 0;
    vector<vector<double>> deltaX(6, vector<double>(1, 1.0));

    vector<vector<double>> A(2 * n, vector<double>(6, 0.0));
    vector<vector<double>> L(2 * n, vector<double>(1, 0.0));
    vector<vector<double>> Q;

    cout << "--- 空间后方交会迭代开始 ---" << endl;

    // 3. 迭代计算核心循环
    while (true) {
        if (abs(deltaX[3][0]) < limit && abs(deltaX[4][0]) < limit && abs(deltaX[5][0]) < limit) {
            break;
        }

        double a1 = cos(phi) * cos(kappa) - sin(phi) * sin(omega) * sin(kappa);
        double a2 = -cos(phi) * sin(kappa) - sin(phi) * sin(omega) * cos(kappa);
        double a3 = -sin(phi) * cos(omega);
        double b1 = cos(omega) * sin(kappa);
        double b2 = cos(omega) * cos(kappa);
        double b3 = -sin(omega);
        double c1 = sin(phi) * cos(kappa) + cos(phi) * sin(omega) * sin(kappa);
        double c2 = -sin(phi) * sin(kappa) + cos(phi) * sin(omega) * cos(kappa);
        double c3 = cos(phi) * cos(omega);

        for (int i = 0; i < n; i++) {
            double dX = pts[i].X - Xs;
            double dY = pts[i].Y - Ys;
            double dZ = pts[i].Z - Zs;

            double X_bar = a1 * dX + b1 * dY + c1 * dZ;
            double Y_bar = a2 * dX + b2 * dY + c2 * dZ;
            double Z_bar = a3 * dX + b3 * dY + c3 * dZ;

            double x_approx = x0 - f * X_bar / Z_bar;
            double y_approx = y0 - f * Y_bar / Z_bar;

            A[2 * i][0] = (a1 * f + a3 * x_approx) / Z_bar;
            A[2 * i][1] = (b1 * f + b3 * x_approx) / Z_bar;
            A[2 * i][2] = (c1 * f + c3 * x_approx) / Z_bar;
            A[2 * i][3] = y_approx * sin(omega) - (x_approx / f * (x_approx * cos(kappa) - y_approx * sin(kappa)) + f * cos(kappa)) * cos(omega);
            A[2 * i][4] = -f * sin(kappa) - x_approx / f * (x_approx * sin(kappa) + y_approx * cos(kappa));
            A[2 * i][5] = y_approx;

            A[2 * i + 1][0] = (a2 * f + a3 * y_approx) / Z_bar;
            A[2 * i + 1][1] = (b2 * f + b3 * y_approx) / Z_bar;
            A[2 * i + 1][2] = (c2 * f + c3 * y_approx) / Z_bar;
            A[2 * i + 1][3] = -x_approx * sin(omega) - (y_approx / f * (x_approx * cos(kappa) - y_approx * sin(kappa)) - f * sin(kappa)) * cos(omega);
            A[2 * i + 1][4] = -f * cos(kappa) - y_approx / f * (x_approx * sin(kappa) + y_approx * cos(kappa));
            A[2 * i + 1][5] = -x_approx;

            L[2 * i][0] = pts[i].x - x_approx;
            L[2 * i + 1][0] = pts[i].y - y_approx;
        }

        vector<vector<double>> AT = Transpose(A);
        vector<vector<double>> ATA = Multiply(AT, A);
        Q = Inverse(ATA);
        vector<vector<double>> ATL = Multiply(AT, L);
        deltaX = Multiply(Q, ATL);

        Xs += deltaX[0][0];
        Ys += deltaX[1][0];
        Zs += deltaX[2][0];
        phi += deltaX[3][0];
        omega += deltaX[4][0];
        kappa += deltaX[5][0];

        iteration++;
        cout << fixed << setprecision(6);
        cout << "第 " << iteration << " 次迭代修正量: "
             << " dXs=" << deltaX[0][0] << ", dYs=" << deltaX[1][0] << ", dZs=" << deltaX[2][0]
             << ", dPhi=" << deltaX[3][0] << ", dOmega=" << deltaX[4][0] << ", dKappa=" << deltaX[5][0] << endl;
    }

    // 4. 精度评定部分
    vector<vector<double>> V(2 * n, vector<double>(1, 0.0));
    double vTv = 0.0;

    vector<vector<double>> A_deltaX = Multiply(A, deltaX);
    for (int i = 0; i < 2 * n; i++) {
        V[i][0] = A_deltaX[i][0] - L[i][0];
        vTv += V[i][0] * V[i][0];
    }

    double sigma0 = sqrt(vTv / (2 * n - 6));

    cout << "\n================= 最终解算结果 =================" << endl;
    cout << fixed << setprecision(4);
    cout << "摄站坐标 (Xs) = " << Xs << " m" << endl;
    cout << "摄站坐标 (Ys) = " << Ys << " m" << endl;
    cout << "摄站坐标 (Zs) = " << Zs << " m" << endl;
    cout << setprecision(6);
    cout << "俯仰角 (Phi)   = " << phi << " rad" << endl;
    cout << "旁向倾角 (Omega) = " << omega << " rad" << endl;
    cout << "旋偏角 (Kappa) = " << kappa << " rad" << endl;
    cout << "总迭代次数 = " << iteration << endl;

    cout << "\n=================== 精度评定 ===================" << endl;
    cout << "单位权中误差 (Sigma0) = " << sigma0 << " mm" << endl;
    cout << "Xs 坐标中误差 = " << sigma0 * sqrt(Q[0][0]) << " m" << endl;
    cout << "Ys 坐标中误差 = " << sigma0 * sqrt(Q[1][1]) << " m" << endl;
    cout << "Zs 坐标中误差 = " << sigma0 * sqrt(Q[2][2]) << " m" << endl;
    cout << "Phi 角度中误差 = " << sigma0 * sqrt(Q[3][3]) << " rad" << endl;
    cout << "Omega 角度中误差 = " << sigma0 * sqrt(Q[4][4]) << " rad" << endl;
    cout << "Kappa 角度中误差 = " << sigma0 * sqrt(Q[5][5]) << " rad" << endl;

    return 0;
}
```
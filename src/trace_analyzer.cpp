#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <fstream>
#include <sstream>
#include <cstring>
#include <iomanip>
#include <memory>

using namespace std;

// Data structure to hold the multi-channel trace
struct TraceData {
    vector<double> t;
    vector<vector<double>> x; // Channels
    vector<double> p; // Trigger/Phase signal
};

// Calculate median of a vector subset
double calculate_median(const vector<double>& data, int start_index, int k) {
    int n = 2 * k + 1;
    vector<double> window;
    window.reserve(n);
    for (int i = 0; i < n; ++i) {
        window.push_back(data[start_index + i]);
    }
    size_t mid = k; // The middle element index
    std::nth_element(window.begin(), window.begin() + mid, window.end());
    return window[mid];
}

// Median filter
void apply_median_filter(const vector<double>& input, vector<double>& output, int k) {
    int n = input.size();
    output.resize(n);
    
    // Copy edges
    for (int i = 0; i < k && i < n; i++) output[i] = input[i];
    for (int i = n - k; i < n && i >= 0; i++) output[i] = input[i];

    // Filter center
    for (int i = k; i < n - k; i++) {
        output[i] = calculate_median(input, i - k, k);
    }
}

int main(int argc, char** argv) {
    // Default parameters
    int filter_width = 5;      // -f
    int max_points = 1000000;  // -l (and default nmax)
    double threshold = 0;      // -q
    double min_period = 2.0;   // -p
    int skip_points = 0;       // -x
    int post_filter_width = 10;// -k
    int win_width = 1000000;   // -W (default nmax)
    double signal_mix = 0;     // -s
    bool voltage_clamp = false;// -vc
    string par_filename = "par"; // Default par filename

    // Hardcoded constants from original
    const int num_channels = 2;
    const int num_phase_bins = 1000;

    // Argument parsing
    for (int i = 1; i < argc; i++) {
        string arg = argv[i];
        if (arg == "-f" && i + 1 < argc) filter_width = atoi(argv[++i]);
        else if (arg == "-l" && i + 1 < argc) max_points = atoi(argv[++i]);
        else if (arg == "-q" && i + 1 < argc) threshold = atof(argv[++i]);
        else if (arg == "-p" && i + 1 < argc) min_period = atof(argv[++i]);
        else if (arg == "-x" && i + 1 < argc) skip_points = atoi(argv[++i]);
        else if (arg == "-k" && i + 1 < argc) post_filter_width = atoi(argv[++i]);
        else if (arg == "-W" && i + 1 < argc) win_width = atoi(argv[++i]);
        else if (arg == "-s" && i + 1 < argc) signal_mix = atof(argv[++i]);
        else if (arg == "-par" && i + 1 < argc) par_filename = argv[++i];
        else if (arg == "-vc") voltage_clamp = true;
        else {
            // Ignore unknown legacy arguments
            if (i + 1 < argc && argv[i+1][0] != '-') i++;
        }
    }

    // Reading data from stdin
    TraceData raw_data;
    raw_data.x.resize(num_channels);

    // Skip points
    for (int i = 0; i < skip_points && cin.good(); i++) {
        double temp;
        cin >> temp; // t
        for (int j = 0; j < num_channels; j++) cin >> temp;
        cin >> temp; // p
    }

    // Read main data
    while (cin.good() && raw_data.t.size() < (size_t)max_points) {
        double val;
        cin >> val;
        if (!cin.good()) break;
        raw_data.t.push_back(val);
        for (int j = 0; j < num_channels; j++) {
            cin >> val;
            raw_data.x[j].push_back(val);
        }
        cin >> val;
        raw_data.p.push_back(val);
    }

    int n = raw_data.t.size();
    if (n == 0) return 0;

    // Filter channels
    vector<vector<double>> filtered_data(num_channels);
    for (int j = 0; j < num_channels; j++) {
        apply_median_filter(raw_data.x[j], filtered_data[j], filter_width);
    }

    // Process trigger/phase signal (p)
    vector<double> p_processed = raw_data.p; // Start with copy of raw p
    vector<double> pp_filtered(n); // Output of processing

    // Signal mixing/normalization logic (if -s is set)
    if (signal_mix != 0) {
        vector<double> pp_temp = raw_data.p; // Copy original p
        for (int i = 0; i < n; i++) {
            double ya = 0, y2 = 0, pa = 0, p2 = 0;
            int cnt = 0;
            int ind = voltage_clamp ? 0 : 1;
            
            int start = max(0, i - win_width);
            int end = min(n, i + win_width);

            for (int j = start; j < end; j++) {
                ya += filtered_data[ind][j];
                y2 += filtered_data[ind][j] * filtered_data[ind][j];
                pa += pp_temp[j];
                p2 += pp_temp[j] * pp_temp[j];
                cnt++;
            }
            
            if (cnt > 0) {
                ya /= cnt;
                // Avoid sqrt of negative due to float precision
                double var_y = max(0.0, y2 / cnt - ya * ya);
                y2 = sqrt(var_y);

                pa /= cnt;
                double var_p = max(0.0, p2 / cnt - pa * pa);
                p2 = sqrt(var_p);
                
                if (p2 != 0 && y2 != 0) {
                     p_processed[i] = (pp_temp[i] - pa) / p2 + signal_mix * (filtered_data[ind][i] - ya) / y2;
                } else {
                     p_processed[i] = 0; // Fallback
                }
            }
        }
    }

    // Filter the processed p signal
    apply_median_filter(p_processed, pp_filtered, post_filter_width);

    // Automatic threshold calculation
    if (threshold <= 0) {
        if (!pp_filtered.empty()) {
            size_t n_samples = pp_filtered.size();
            vector<double> sorted_pp = pp_filtered;
            size_t mid_idx = n_samples / 2;
            
            // 1. Calculate Median
            std::nth_element(sorted_pp.begin(), sorted_pp.begin() + mid_idx, sorted_pp.end());
            double median = sorted_pp[mid_idx];
            
            // 2. Calculate Absolute Deviations
            vector<double> deviations(n_samples);
            for(size_t i=0; i<n_samples; ++i) {
                deviations[i] = std::abs(pp_filtered[i] - median);
            }
            
            // 3. Calculate MAD (Median Absolute Deviation)
            std::nth_element(deviations.begin(), deviations.begin() + mid_idx, deviations.end());
            double mad = deviations[mid_idx];
            
            // 4. Set Threshold using robust statistics (Gaussian equivalent)
            // K * 1.4826 * MAD approximates K * Sigma for Gaussian noise.
            // We use K=4.0 to safely clear the noise floor while catching spikes.
            const double sigma_est = 1.4826 * mad;
            threshold = median + 4.0 * sigma_est;
            
            // Fallback for extremely clean signals where MAD might be 0 due to quantization
            if (mad < 1e-9) {
                // Use Standard Deviation as fallback
                double mean = 0, sq_sum = 0;
                for(double v : pp_filtered) mean += v;
                mean /= n_samples;
                for(double v : pp_filtered) sq_sum += (v-mean)*(v-mean);
                double std_dev = sqrt(sq_sum / n_samples);
                threshold = mean + 3.0 * std_dev;
                
                // If still zero, just start slightly above median
                if (threshold <= median) threshold = median + 1e-6;
            }
            
        } else {
            threshold = 0;
        }
    }

    // Cycle Detection and Phase Calculation
    vector<double> phase(n, -1.0);
    double T_sum = 0, T2_sum = 0;
    int cycle_count = 0;
    int prev_idx = 0; // ipre

    // Logic from original: loop range [kkk, n-kkk)
    // kkk is filter_width
    int start_loop = filter_width;
    int end_loop = n - filter_width;

    for (int i = start_loop; i < end_loop; i++) {
        // Trigger on rising edge crossing threshold
        if (pp_filtered[i - 1] < threshold && pp_filtered[i] >= threshold) {
            double current_time = raw_data.t[i];
            double prev_time = raw_data.t[prev_idx];
            
            if (prev_idx != 0 && (current_time - prev_time) > min_period) {
                double period = current_time - prev_time;
                T_sum += period;
                T2_sum += period * period;
                cycle_count++;

                // Assign phase to previous cycle
                for (int j = prev_idx; j < i; j++) {
                    phase[j] = (raw_data.t[j] - prev_time) / period;
                }
            }
            
            if (prev_idx == 0 || (current_time - prev_time) > min_period) {
                prev_idx = i;
            }
        }
    }

    // Binning and Regression
    // Stats accumulators
    vector<double> M0(num_phase_bins, 0.0), M1(num_phase_bins, 0.0);
    vector<double> X00(num_phase_bins, 0.0), X01(num_phase_bins, 0.0), X11(num_phase_bins, 0.0);
    vector<int> counts(num_phase_bins, 0);

    for (int i = 0; i < n; i++) {
        if (phase[i] >= 0) {
            int bin = floor(phase[i] * num_phase_bins);
            if (bin >= num_phase_bins) bin = num_phase_bins - 1; // Clamp

            double y0 = filtered_data[0][i];
            double y1 = filtered_data[1][i];

            M0[bin] += y0;
            M1[bin] += y1;
            X00[bin] += y0 * y0;
            X01[bin] += y0 * y1;
            X11[bin] += y1 * y1;
            counts[bin]++;
        }
    }

    // Output stats to stderr (the 'ph' file content)
    for (int l = 0; l < num_phase_bins; l++) {
        if (counts[l] > 0) {
            M0[l] /= counts[l];
            M1[l] /= counts[l];
            X00[l] /= counts[l];
            X01[l] /= counts[l];
            X11[l] /= counts[l];

            double cov = X01[l] - M0[l] * M1[l];
            double var1 = X11[l] - M1[l] * M1[l];
            double var0 = X00[l] - M0[l] * M0[l];

            // Regression 1: Ch0 = a * Ch1 + b
            // Slope a
            double a = (var1 != 0) ? cov / var1 : 0;
            double b = M0[l] - a * M1[l];
            double err = (var1 != 0) ? sqrt(max(0.0, var0 / var1 - a * a)) : 0;

            // Regression 2: Ch1 = aa * Ch0 + bb
            double aa = (var0 != 0) ? cov / var0 : 0;
            double bb = M1[l] - aa * M0[l];
            double erer = (var0 != 0) ? sqrt(max(0.0, var1 / var0 - aa * aa)) : 0;

            if (voltage_clamp) {
                 cerr << a << '\t' << b << '\t' << err << '\t' << counts[l] << endl;
            } else {
                 // Convert Regression 2 back to Ch0 vs Ch1 form
                 double inv_aa = (aa != 0) ? 1.0 / aa : 0; // Slope
                 double intercept = (aa != 0) ? -bb / aa : 0; // Intercept
                 double error_transformed = (aa != 0) ? erer / (aa * aa) : 0; // Error scaling?
                 
                 cerr << inv_aa << '\t' << intercept << '\t' << error_transformed << '\t' << counts[l] << endl;
            }
        }
        // Omit empty bins to avoid gnuplot errors
    }

    // Output processed traces to stdout (the 'dat' file content)
    // Range: [kkk, n-kkk)
    cout << setprecision(6) << fixed;
    for (int i = start_loop; i < end_loop; i++) {
        cout << raw_data.t[i] << '\t'
             << pp_filtered[i] << '\t'
             << phase[i] << '\t'
             << filtered_data[0][i] << '\t'
             << filtered_data[1][i] << endl;
    }

    // Output Parameters to 'par' file
    if (cycle_count > 0) {
        T_sum /= cycle_count;
        T2_sum /= cycle_count;
    }
    double dT = sqrt(max(0.0, T2_sum - T_sum * T_sum));
    
    ofstream par_file(par_filename.c_str());
    par_file << "Ta=" << T_sum << endl;
    par_file << "dTa=" << dT << endl;
    par_file << "q=" << threshold << endl;
    par_file.close();

    return 0;
}

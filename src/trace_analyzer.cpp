#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

using namespace std;

// Data structure to hold the multi-channel trace
struct TraceData {
  vector<double> t;
  vector<vector<double>> x; // Channels
  vector<double> p;         // Trigger/Phase signal
};

// Calculate median of a vector subset
double calculate_median(const vector<double> &data, int start_index, int k) {
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
void apply_median_filter(const vector<double> &input, vector<double> &output,
                         int k) {
  int n = input.size();
  output.resize(n);

  // Copy edges
  for (int i = 0; i < k && i < n; i++)
    output[i] = input[i];
  for (int i = n - k; i < n && i >= 0; i++)
    output[i] = input[i];

  // Filter center
  for (int i = k; i < n - k; i++) {
    output[i] = calculate_median(input, i - k, k);
  }
}

void calculate_median_and_mad(const vector<double> &data, double &median,
                              double &mad) {
  if (data.empty()) {
    median = 0;
    mad = 0;
    return;
  }
  vector<double> sorted = data;
  size_t n = sorted.size();
  size_t mid_idx = n / 2;
  std::nth_element(sorted.begin(), sorted.begin() + mid_idx, sorted.end());
  median = sorted[mid_idx];

  vector<double> deviations(n);
  for (size_t i = 0; i < n; ++i) {
    deviations[i] = std::abs(data[i] - median);
  }
  std::nth_element(deviations.begin(), deviations.begin() + mid_idx,
                   deviations.end());
  mad = deviations[mid_idx] * 1.4826 * 2.0;
}

int main(int argc, char **argv) {
  // Default parameters
  int filter_width = 5;       // -f
  int max_points = 1000000;   // -l (and default nmax)
  double threshold = 0;       // -q
  double min_period = 2.0;    // -p
  int skip_points = 0;        // -x
  int post_filter_width = 10; // -k
  int win_width = 1000000;    // -W (default nmax)
  double signal_mix = 0;      // -s
  bool voltage_clamp = false; // -vc
  double Ei = -80.0;          // -Ei
  double Ee = -10.0;          // -Ee
  double threshold_multiplier =
      2.5;                     // -m, default lowered from 4.0 (and 3.0) to 2.5
  int min_duration = 10;       // -w, minimum duration in samples
  string par_filename = "par"; // Default par filename

  // Hardcoded constants from original
  const int num_channels = 2;
  const int num_phase_bins = 1000;

  // Argument parsing
  for (int i = 1; i < argc; i++) {
    string arg = argv[i];
    if (arg == "-f" && i + 1 < argc)
      filter_width = atoi(argv[++i]);
    else if (arg == "-l" && i + 1 < argc)
      max_points = atoi(argv[++i]);
    else if (arg == "-q" && i + 1 < argc)
      threshold = atof(argv[++i]);
    else if (arg == "-p" && i + 1 < argc)
      min_period = atof(argv[++i]);
    else if (arg == "-x" && i + 1 < argc)
      skip_points = atoi(argv[++i]);
    else if (arg == "-k" && i + 1 < argc)
      post_filter_width = atoi(argv[++i]);
    else if (arg == "-W" && i + 1 < argc)
      win_width = atoi(argv[++i]);
    else if (arg == "-s" && i + 1 < argc)
      signal_mix = atof(argv[++i]);
    else if (arg == "-m" && i + 1 < argc)
      threshold_multiplier = atof(argv[++i]);
    else if (arg == "-w" && i + 1 < argc)
      min_duration = atoi(argv[++i]);
    else if (arg == "-par" && i + 1 < argc)
      par_filename = argv[++i];
    else if (arg == "-vc")
      voltage_clamp = true;
    else if (arg == "-Ei" && i + 1 < argc)
      Ei = atof(argv[++i]);
    else if (arg == "-Ee" && i + 1 < argc)
      Ee = atof(argv[++i]);
    else {
      // Ignore unknown legacy arguments
      if (i + 1 < argc && argv[i + 1][0] != '-')
        i++;
    }
  }

  // Reading data from stdin
  TraceData raw_data;
  raw_data.x.resize(num_channels);

  // Skip points
  for (int i = 0; i < skip_points && cin.good(); i++) {
    double temp;
    cin >> temp; // t
    for (int j = 0; j < num_channels; j++)
      cin >> temp;
    cin >> temp; // p
  }

  // Read main data
  while (cin.good() && raw_data.t.size() < (size_t)max_points) {
    double val;
    cin >> val;
    if (!cin.good())
      break;
    raw_data.t.push_back(val);
    for (int j = 0; j < num_channels; j++) {
      cin >> val;
      raw_data.x[j].push_back(val);
    }
    cin >> val;
    raw_data.p.push_back(val);
  }

  int n = raw_data.t.size();
  if (n == 0)
    return 0;

  // Filter channels
  vector<vector<double>> filtered_data(num_channels);
  for (int j = 0; j < num_channels; j++) {
    apply_median_filter(raw_data.x[j], filtered_data[j], filter_width);
  }

  // Process trigger/phase signal (p)
  vector<double> p_processed = raw_data.p; // Start with copy of raw p
  vector<double> pp_filtered(n);           // Output of processing

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
          p_processed[i] = (pp_temp[i] - pa) / p2 +
                           signal_mix * (filtered_data[ind][i] - ya) / y2;
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
      std::nth_element(sorted_pp.begin(), sorted_pp.begin() + mid_idx,
                       sorted_pp.end());
      double median = sorted_pp[mid_idx];

      // 2. Calculate Absolute Deviations
      vector<double> deviations(n_samples);
      for (size_t i = 0; i < n_samples; ++i) {
        deviations[i] = std::abs(pp_filtered[i] - median);
      }

      // 3. Calculate MAD (Median Absolute Deviation)
      std::nth_element(deviations.begin(), deviations.begin() + mid_idx,
                       deviations.end());
      double mad = deviations[mid_idx];

      // 4. Set Threshold using robust statistics (Gaussian equivalent)
      // K * 1.4826 * MAD approximates K * Sigma for Gaussian noise.
      // We use K=threshold_multiplier (default 2.5) to safely clear the noise
      // floor while catching spikes.
      const double sigma_est = 1.4826 * mad;
      threshold = median + threshold_multiplier * sigma_est;

      // Fallback for extremely clean signals where MAD might be 0 due to
      // quantization
      if (mad < 1e-9) {
        // Use Standard Deviation as fallback
        double mean = 0, sq_sum = 0;
        for (double v : pp_filtered)
          mean += v;
        mean /= n_samples;
        for (double v : pp_filtered)
          sq_sum += (v - mean) * (v - mean);
        double std_dev = sqrt(sq_sum / n_samples);
        threshold = mean + 3.0 * std_dev;

        // If still zero, just start slightly above median
        if (threshold <= median)
          threshold = median + 1e-6;
      }

    } else {
      threshold = 0;
    }
  }

  // Cycle Detection and Phase Calculation
  vector<double> phase(n, -1.0);
  double T_sum = 0, T2_sum = 0;
  double D_sum = 0; // Sum of durations
  int cycle_count = 0;
  int prev_idx = 0; // ipre

  // Logic from original: loop range [kkk, n-kkk)
  // kkk is filter_width
  int start_loop = filter_width;
  int end_loop = n - filter_width;

  for (int i = start_loop; i < end_loop; i++) {
    // Simple threshold crossing check for rising edge
    bool crossing =
        (pp_filtered[i - 1] < threshold && pp_filtered[i] >= threshold);

    if (crossing) {
      // Check duration
      int k = 0;
      bool valid_pulse = true;
      // Check if it stays above threshold for min_duration
      for (k = 0; k < min_duration; k++) {
        if (i + k >= n || pp_filtered[i + k] < threshold) {
          valid_pulse = false;
          break;
        }
      }

      if (valid_pulse) {
        double current_time = raw_data.t[i];
        double prev_time = raw_data.t[prev_idx];

        if (prev_idx != 0 && (current_time - prev_time) > min_period) {
          double period = current_time - prev_time;
          T_sum += period;
          T2_sum += period * period;
          cycle_count++;

          // Calculate duration of the PREVIOUS pulse
          // We need to find when the previous pulse ended.
          // Since we don't track it explicitly, let's look for falling edge
          // starting from prev_idx.
          // Note: This simple logic assumes the signal drops below threshold
          // before the next rising edge, which is guaranteed by the `crossing`
          // check.
          double pulse_start_time = raw_data.t[prev_idx];
          double pulse_end_time = pulse_start_time;

          // Search for falling edge
          for (int j = prev_idx; j < i; j++) {
            if (pp_filtered[j] < threshold) {
              // Interpolate falling edge time? Or just take t[j]?
              // Let's just take t[j] as the first point below threshold
              pulse_end_time = raw_data.t[j];
              break;
            }
          }
          // If we didn't find a falling edge (signal stayed high the whole
          // time?), then duration is effectively the period. But that shouldn't
          // happen if we have a rising edge at 'i'.

          D_sum += (pulse_end_time - pulse_start_time);

          // Assign phase to previous cycle
          for (int j = prev_idx; j < i; j++) {
            phase[j] = (raw_data.t[j] - prev_time) / period;
          }
        }

        if (prev_idx == 0 || (current_time - prev_time) > min_period) {
          prev_idx = i;
        }

        // Fast forward to end of pulse to avoid re-triggering?
        // Or just let basic rising edge logic handle it (sine pp[i-1] needs to
        // be < thresh) The loop continues, next sample pp[i] will be >= thresh,
        // so pp[i-1] for next iter is >= thresh. So rising edge check fails.
        // Correct.
      }
    }
  }

  // Binning and Regression
  // Stats accumulators
  vector<double> M0(num_phase_bins, 0.0), M1(num_phase_bins, 0.0);
  vector<double> X00(num_phase_bins, 0.0), X01(num_phase_bins, 0.0),
      X11(num_phase_bins, 0.0);
  vector<int> counts(num_phase_bins, 0);

  for (int i = 0; i < n; i++) {
    if (phase[i] >= 0) {
      int bin = floor(phase[i] * num_phase_bins);
      if (bin >= num_phase_bins)
        bin = num_phase_bins - 1; // Clamp

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

  // Store regression results
  struct RegResult {
    double slope;
    double intercept;
    double error;
    int count;
  };
  vector<RegResult> results(num_phase_bins);
  bool has_data = false;

  // Calculate stats first
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
        results[l] = {a, b, err, counts[l]};
      } else {
        // Convert Regression 2 back to Ch0 vs Ch1 form
        double inv_aa = (aa != 0) ? 1.0 / aa : 0;    // Slope
        double intercept = (aa != 0) ? -bb / aa : 0; // Intercept
        double error_transformed =
            (aa != 0) ? erer / (aa * aa) : 0; // Error scaling?
        results[l] = {inv_aa, intercept, error_transformed, counts[l]};
      }
      has_data = true;
    } else {
      results[l] = {0, 0, 0, 0};
    }
  }

  // Calculate derived parameters (replacing Gnuplot stats)
  double Ii = -1e9, Ie = 1e9; // Initialize with extremes
  double G_sum = 0, I_sum = 0;
  long long total_records = 0;

  if (has_data) {
    // First pass for Ii, Ie (max/min projections)
    // And Accumulate for G, I (means)
    for (int l = 0; l < num_phase_bins; l++) {
      if (results[l].count > 0) {
        double slope = results[l].slope;
        double intercept = results[l].intercept;

        double term_i = intercept + Ei * slope;
        if (term_i > Ii)
          Ii = term_i; // max

        double term_e = intercept + Ee * slope;
        if (term_e < Ie)
          Ie = term_e; // min

        G_sum += slope;
        I_sum += intercept;
        total_records++;
      }
    }
  } else {
    Ii = 0;
    Ie = 0;
  }

  double G = (total_records > 0) ? G_sum / total_records : 1e-9;
  double I = (total_records > 0) ? I_sum / total_records : 0;

  double g = 1e-9;
  double E = 0;
  if (Ee != Ei && (Ie - Ii) != 0) {
    g = (Ie - Ii) / (Ee - Ei);
    E = Ei - Ii / g;
  }

  // Pre-calculate Conductances and Collect Stats
  vector<double> all_Ginh;
  vector<double> all_Gexc;
  struct BinData {
    double G_inh;
    double G_exc;
    bool valid;
  };
  vector<BinData> bin_data(num_phase_bins);

  for (int l = 0; l < num_phase_bins; l++) {
    if (results[l].count > 0 && g != 0) {
      double slope = results[l].slope;
      double intercept = results[l].intercept;
      double G_inh = (Ee * (slope - g) - (-intercept - g * E)) / (Ee - Ei) / g;
      double G_exc =
          (slope - (Ee * (slope - g) - (-intercept - g * E)) / (Ee - Ei) - g) /
          g;

      bin_data[l] = {G_inh, G_exc, true};
      all_Ginh.push_back(G_inh);
      all_Gexc.push_back(G_exc);
    } else {
      bin_data[l] = {0, 0, false};
    }
  }

  // Calculate Median/MAD/Sigma
  double Gi0 = 0, dGi = 0, Ge0 = 0, dGe = 0;
  calculate_median_and_mad(all_Ginh, Gi0, dGi);
  calculate_median_and_mad(all_Gexc, Ge0, dGe);
  // Scale MAD simply by 2 * 1.4826 to get the 2*Sigma threshold directly
  double dGi_thresh =
      dGi; // Already scaled in function? Wait, let's check function.
           // Function (as currently modified) calculates MAD*1.4826*2.
           // So dGi IS the 2*Sigma threshold. Correct.

  // Determine "Transient" status for each bin
  vector<bool> is_outside(num_phase_bins, false);
  for (int l = 0; l < num_phase_bins; ++l) {
    if (bin_data[l].valid) {
      if (abs(bin_data[l].G_inh - Gi0) > dGi ||
          abs(bin_data[l].G_exc - Ge0) > dGe) {
        is_outside[l] = true;
      }
    }
  }

  // Find Longest Consecutive Chain (Cyclic)
  int max_len = 0;
  int best_start = -1;

  // Simple approach for cyclic: concatenate is_outside to itself
  vector<bool> double_outside = is_outside;
  double_outside.insert(double_outside.end(), is_outside.begin(),
                        is_outside.end());

  int current_len = 0;
  int current_start = -1;

  for (size_t i = 0; i < double_outside.size(); ++i) {
    if (double_outside[i]) {
      if (current_len == 0)
        current_start = i;
      current_len++;
    } else {
      if (current_len > max_len) {
        max_len = current_len;
        best_start = current_start;
      }
      current_len = 0;
    }
  }
  // Check end case
  if (current_len > max_len) {
    max_len = current_len;
    best_start = current_start;
  }

  // Determine Transient Start/End
  int tr_start = -1;
  int tr_end = -1;

  if (max_len > 0) {
    tr_start = best_start % num_phase_bins;
    tr_end = (best_start + max_len - 1) % num_phase_bins;
  }

  // Calculate Means for Transient (tr) and Stationary (st) intervals
  double sum_Ginh_tr = 0, sum_Gexc_tr = 0;
  double sum_Ginh_st = 0, sum_Gexc_st = 0;
  int count_tr = 0, count_st = 0;

  for (int l = 0; l < num_phase_bins; ++l) {
    if (bin_data[l].valid) {
      // Check if bin l is transient
      bool is_tr = false;
      if (tr_start != -1) {
        if (tr_start <= tr_end) {
          is_tr = (l >= tr_start && l <= tr_end);
        } else {
          is_tr = (l >= tr_start || l <= tr_end);
        }
      }

      if (is_tr) {
        sum_Ginh_tr += bin_data[l].G_inh;
        sum_Gexc_tr += bin_data[l].G_exc;
        count_tr++;
      } else {
        sum_Ginh_st += bin_data[l].G_inh;
        sum_Gexc_st += bin_data[l].G_exc;
        count_st++;
      }
    }
  }

  double G_inh_tr = (count_tr > 0) ? sum_Ginh_tr / count_tr : 0;
  double G_exc_tr = (count_tr > 0) ? sum_Gexc_tr / count_tr : 0;
  double G_inh_st = (count_st > 0) ? sum_Ginh_st / count_st : 0;
  double G_exc_st = (count_st > 0) ? sum_Gexc_st / count_st : 0;

  // Calculate Min/Max Conductances
  double G_inh_min = 1e9, G_inh_max = -1e9;
  double G_exc_min = 1e9, G_exc_max = -1e9;
  bool found_valid_cond = false;

  for (const auto& bin : bin_data) {
      if (bin.valid) {
          if (bin.G_inh < G_inh_min) G_inh_min = bin.G_inh;
          if (bin.G_inh > G_inh_max) G_inh_max = bin.G_inh;
          if (bin.G_exc < G_exc_min) G_exc_min = bin.G_exc;
          if (bin.G_exc > G_exc_max) G_exc_max = bin.G_exc;
          found_valid_cond = true;
      }
  }
  
  if (!found_valid_cond) {
      G_inh_min = G_inh_max = 0;
      G_exc_min = G_exc_max = 0;
  }

  // Output stats to stderr (the 'ph' file content)
  for (int l = 0; l < num_phase_bins; l++) {
    if (results[l].count > 0) {
      double slope = results[l].slope;
      double intercept = results[l].intercept;

      // Use stored values
      double G_inh = bin_data[l].G_inh;
      double G_exc = bin_data[l].G_exc;

      cerr << slope << '\t' << intercept << '\t' << results[l].error << '\t'
           << results[l].count << '\t' << G_inh << '\t' << G_exc << '\t' << l
           << endl;
    }
    // Omit empty bins to avoid gnuplot errors
  }

  // Output processed traces to stdout (the 'dat' file content)
  // Range: [kkk, n-kkk)
  cout << setprecision(6) << fixed;
  for (int i = start_loop; i < end_loop; i++) {
    cout << raw_data.t[i] << '\t' << pp_filtered[i] << '\t' << phase[i] << '\t'
         << filtered_data[0][i] << '\t' << filtered_data[1][i] << endl;
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
  par_file << "Du=" << (T_sum > 0 ? (D_sum / cycle_count) / T_sum : 0) << endl;
  par_file << "G=" << G << endl;
  par_file << "I=" << I << endl;
  par_file << "g=" << g << endl;
  par_file << "E=" << E << endl;
  par_file << "Ii=" << Ii << endl;
  par_file << "Ie=" << Ie << endl;
  par_file << "Ei=" << Ei << endl;
  par_file << "Ee=" << Ee << endl;

  // Output threshold values (remember function scales by 2*1.4826 already)
  par_file << "Gi0=" << Gi0 << endl;
  par_file << "dGi=" << dGi << endl;
  par_file << "Ge0=" << Ge0 << endl;
  par_file << "dGe=" << dGe << endl;

  // Output Transient Range
  par_file << "tr_start=" << tr_start << endl;
  par_file << "tr_end=" << tr_end << endl;

  // Output Interval Means
  par_file << "G_inh_tr=" << G_inh_tr << endl;
  par_file << "G_exc_tr=" << G_exc_tr << endl;
  par_file << "G_inh_st=" << G_inh_st << endl;
  par_file << "G_exc_st=" << G_exc_st << endl;

  // Output Min/Max Conductances
  par_file << "G_inh_min=" << G_inh_min << endl;
  par_file << "G_inh_max=" << G_inh_max << endl;
  par_file << "G_exc_min=" << G_exc_min << endl;
  par_file << "G_exc_max=" << G_exc_max << endl;

  par_file << "q=" << threshold << endl;
  par_file.close();

  return 0;
}

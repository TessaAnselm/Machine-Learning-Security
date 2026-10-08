# ThreatVote AI

ThreatVote AI is an interactive learning app for exploring how machine learning detects attacks in network traffic. Monster, an animated cookie-loving guide, leads you through three hands-on missions: guess the winning detector, compare models, and investigate mistakes.

Each model predicts **benign traffic** or **attack traffic**. Attack names such as `DDoS` and `PortScan` help you inspect mistakes; the models do not predict the attack type.

**The app starts with a bundled synthetic dataset.** You can try it without downloading data. Use the sample to learn how the app works; its scores do not measure real-world detection performance.

## Quick start

You need Python and **Node.js 22.12 or newer** (with npm). Choose either Conda or Python's built-in virtual environment (`venv`) for the backend. Run the commands from the project folder; skip `cd threatvote-ai` if your terminal is already there.

### Option 1: Conda

With Conda installed, create and activate an environment, then install the project's dependencies with pip:

```bash
cd threatvote-ai
conda create -n threatvote-ai python pip
conda activate threatvote-ai
python -m pip install -r requirements.txt
```

If the environment already exists, skip `conda create`. These commands also work in an Anaconda Prompt on Windows.

### Option 2: venv

You need Python and pip installed:

```bash
cd threatvote-ai
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, use `python` instead of `python3` and activate the environment with the command for your shell:

```powershell
# PowerShell
.venv\Scripts\Activate.ps1
```

```bat
:: Command Prompt
.venv\Scripts\activate.bat
```

### Prepare the app (first-time setup)

```bash
cd frontend
npm ci
npm run build
cd ..
```

### Start the app

With your Python environment activated, run from the project folder:

```bash
python server.py
```

Open **[localhost:8000](http://localhost:8000)** in your browser. The first experiment trains all four models before showing the results. Keep the terminal running; press Ctrl+C to stop it.

### Open the app again later

From the project folder, run:

```bash
conda activate threatvote-ai
python server.py
```

Then open **[localhost:8000](http://localhost:8000)**. If you chose venv, activate `.venv` instead of running the Conda command.

## Try the app

1. Start with the default **Synthetic demo data**.
2. Follow the animated Monster guide in **Meet the traffic**. Pick the detector you think catches the most attacks, then click **Check my guess**.
3. Click **Compare detectors** to compare two detectors. Choose your favorite after checking missed attacks and false alarms.
4. In **Find the mistakes**, answer Monster's question and inspect a detector's mistakes. Finish all three missions to complete the adventure.
5. For another experiment, open **Lab settings** in the sidebar and change one setting, then click **Apply & retrain**. Mission progress resets after successful retraining. If training fails, the previous results and progress remain available.

Use the mission sidebar to navigate at any time. Monster talks with mouth movements, blinks, and bites and chews its cookie in a silent looping GIF. It also wiggles to celebrate successful answers and choices. Turn off **Animate Monster** for a still character; the animation also respects your device's reduced-motion preference. Your motion preference is saved in the browser; mission progress lasts for the current page session.

The app shows one mission at a time:

| Mission | What you can do |
| --- | --- |
| **Meet the traffic** | Guess the winning detector, reveal its results, and explore labeled traffic. |
| **Compare detectors** | Compare two detectors side by side and choose one; expand scores and confusion matrices for more detail. |
| **Find the mistakes** | Answer a missed-attack question and inspect false alarms and missed attacks by family. |

**Lab settings** is collapsed initially and contains the data source, test-set size, random seed, tree depth, number of forest trees, boosting iterations, and learning rate. Edits are applied only when you click **Apply & retrain**. Keeping the same settings and random seed makes runs repeatable. A visible demo-data notice identifies the synthetic sample.

## Understand the results

The app trains models on one portion of the data and evaluates them on a separate **test set**. By default, 75% of the rows are used for training and 25% for testing.

| Metric | What it tells you |
| --- | --- |
| **Accuracy** | Of all test rows, how many were classified correctly? |
| **Precision** | Of the rows flagged as attacks, how many were actually attacks? |
| **Recall** | Of the actual attacks, how many did the model catch? |
| **F1** | A combined score that balances precision and recall. |

Scores range from 0 to 1; higher is better. Accuracy alone can be misleading when most traffic is benign, so compare precision and recall too.

A **confusion matrix** counts correct predictions and mistakes. Its rows show the actual label, and its columns show the predicted label:

- **True positive:** an attack correctly flagged.
- **True negative:** benign traffic correctly classified.
- **False positive:** benign traffic flagged as an attack—a false alarm.
- **False negative:** an attack classified as benign—a missed attack.

## Models compared

| Model | How it works |
| --- | --- |
| **Decision Tree** | Learns a sequence of rules from traffic features. |
| **Random Forest** | Combines many decision trees to make a prediction. |
| **AdaBoost** | Builds a sequence of small models, giving more attention to examples that earlier models got wrong. |
| **Voting Ensemble** | Averages the attack probabilities from a Decision Tree, Random Forest, and AdaBoost model to make a final prediction. |

Combining models is called **ensemble learning**. It can improve results, but the voting ensemble is not guaranteed to outperform every individual model.

## Data sources

### Bundled sample

`data/sample/cicids2017_sample.csv` contains 4,000 synthetic rows with CIC-IDS2017-style traffic features and six labels: `BENIGN`, `DoS Hulk`, `DDoS`, `PortScan`, `Bot`, and `Web Attack - Brute Force`.

The sample is generated with a fixed random seed. If the file is missing, the app creates it automatically. To regenerate it manually:

```bash
python data.py
```

### Real CIC-IDS2017 data (optional)

1. Download the labeled flow CSVs (the `GeneratedLabelledFlows` files) from the [Canadian Institute for Cybersecurity's CIC-IDS2017 page](https://www.unb.ca/cic/datasets/ids-2017.html).
2. Create a `data/raw/` folder and copy the extracted `.csv` files into it. For example: `data/raw/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv`.
3. Refresh the page, open **Lab settings**, and select a file in **Traffic source**. Each file is a separate data source.
4. Adjust **Maximum rows** to control how many cleaned rows are used for training and testing, then click **Apply & retrain**. The default is 20,000; larger samples may take longer to train.

`data/raw/` is ignored by Git. Keep downloaded datasets out of commits.

## How data is prepared

Both data sources follow the same process:

1. Remove identifying columns: Flow ID, source IP, destination IP, source port, and timestamp.
2. Convert traffic features to numbers and remove rows with missing or infinite values.
3. Remove exact duplicate rows after cleaning.
4. Split the data once into training and test sets, preserving attack-family proportions when possible. If a family has fewer than two rows, the split uses benign/attack proportions instead.
5. Train all four models on the same training set and score them on the same test set.

The original attack-family label is excluded from the input features. No scaler or other preprocessing is fitted on the full dataset before the split. These choices reduce **data leakage**, where information from the test set makes results look better than they should.

This is an educational lab for labeled CSV data. Its test scores describe the selected dataset and split; they do not establish performance on live network traffic.

## Working on the code

For code changes, tests, and animation tools, see the [developer guide](DEVELOPMENT.md).

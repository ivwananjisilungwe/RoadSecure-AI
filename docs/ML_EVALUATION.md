# Machine-learning evaluation

RoadSecure evaluates three detection strategies on the same 2,000 held-out synthetic events. The hybrid detector found 353 of 400 labelled anomalies, compared with 259 for rules alone. Rules alone achieved the best accuracy and F1 score and raised 264 fewer false alerts than the hybrid strategy.

## Reproduce the experiment

From the repository root, install the backend requirements and execute:

```sh
cd backend
python -m pip install -r requirements.txt
python -m app.detection train
python -m app.detection evaluate
python -m pytest tests/test_detection.py -q
```

Training creates a local Joblib pipeline and `evaluation.json` under `database/runtime/`, or under the directory specified by `ROADSECURE_DATA_DIR`. The evaluation command reloads the pipeline, verifies the regenerated test dataset against its fingerprint, and reruns the test experiment with fresh latency measurements. Use locally generated model artifacts only. Retrain after changes to dependencies, the feature schema or synthetic distributions.

## Dataset and model

| Split | Seed | Events | Labelled anomalies | Purpose |
| --- | ---: | ---: | ---: | --- |
| Training | 42 | 5,000 | 0 | Fit StandardScaler and Isolation Forest on normal activity |
| Validation | 1042 | 1,000 | 200 | Select the anomaly-score threshold by maximum model F1, breaking ties by lowest false-positive rate |
| Test | 2042 | 2,000 | 400 | Compare the three frozen strategies against the same labels |

The generator models fictional transport portals, administrator work and device activity. Normal records sometimes contain out-of-hours activity, new devices and legitimate privileged actions. Anomalous records include combinations of indicators and borderline cases whose features overlap with normal records. Exact feature duplicates across all three splits cause training to fail. Each split has a SHA-256 fingerprint in the generated report.

The eight model features are failed login count, requests per minute, data transfer in MB, outside-hours flag, unknown-device flag, unusual-location flag, privileged-action flag and number of sensitive records accessed. The pipeline applies StandardScaler and an Isolation Forest with 180 trees, random state 42 and a configured contamination value of 0.06. Serving uses a validation-selected cutoff of 0.4697628196040566 on the negated scikit-learn sample score. A larger score indicates a more atypical observation relative to the training records. The score is uncalibrated.

## Alert policy

| Rule | Trigger | Risk points |
| --- | --- | ---: |
| RS-01 | At least five failures in the event's login aggregate | 25 |
| RS-02 | Outside-hours telemetry flag | 15 |
| RS-03 | Unknown-device telemetry flag | 20 |
| RS-04 | Transfer over 40 MB | 25 |
| RS-05 | Privileged action with an explicit suspicious-context flag | 35 |
| RS-06 | Sensitive access involving at least 30 records | 30 |
| Isolation Forest | Sample meets the validation-selected cutoff | 20 |

Risk is the sum of distinct matched contributions, capped at 100. Risk bands are LOW 0–24, MEDIUM 25–49, HIGH 50–74 and CRITICAL 75–100. The point weights and severity bands are prototype policy. The hybrid policy alerts on any rule match or a positive model result, including LOW alerts. The rules-only policy alerts on any rule match and the model-only policy alerts when the same model cutoff is met.

## Executed results

Observed with Python 3.12.14, scikit-learn 1.8.0, NumPy 2.3.5 and Joblib 1.5.3. [Recorded evaluation JSON](ml-evaluation-results.json)

| Strategy | Accuracy | Precision | Recall | F1 | False-positive rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Rules | 85.95% | 64.91% | 64.75% | 64.83% | 8.75% |
| Isolation Forest | 77.40% | 46.56% | 88.00% | 60.90% | 25.25% |
| Hybrid | 77.45% | 46.63% | 88.25% | 61.02% | 25.25% |

| Strategy | True positive | True negative | False positive | False negative | Mean ms | Median ms | P95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Rules | 259 | 1460 | 140 | 141 | 0.000628 | 0.000509 | 0.000951 |
| Isolation Forest | 352 | 1196 | 404 | 48 | 6.939 | 6.606 | 9.213 |
| Hybrid | 353 | 1196 | 404 | 47 | 7.084 | 6.380 | 11.436 |

Latency is measured around each in-process decision after one warm-up call per strategy. Request transport, database writes and browser rendering are outside this measurement.

The model flagged the demo's legitimate administrative action as an anomaly, producing a LOW alert with no matched rules. Use the findings and contextual event data to explain why alerts require analyst review. Synthetic labels, feature distributions, thresholds and timing characterize this prototype. Generalizing to real transport workloads requires authorized representative telemetry and prospective evaluation. Indicators such as device trust and access hours come from submitted synthetic records. Failed logins use an event-supplied aggregate.

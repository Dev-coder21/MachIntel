# Model Evaluation & Selection Protocol

## Selection Rule
To preserve scientific rigor, the selection rule is defined strictly **prior** to viewing test results:
> **Selection Rule:** The candidate model achieving the lowest Root Mean Squared Error (RMSE) on the held-out `INTERNAL_VAL` split (Units 81–100) shall be designated as the active model for production serving.

No test set feedback or tuning against `EVAL_TEST` is permitted in selecting the active model.

## Observed Empirical Results

| Metric | Split | Ridge Regression (`rul-ridge-v1.0.0`) | Random Forest (`rul-randomforest-v1.0.0`) | Best |
| :--- | :--- | :--- | :--- | :--- |
| **Validation RMSE** | `INTERNAL_VAL` (4,493 samples) | 20.1441 | **19.5411** | **Random Forest** |
| **Validation PHM Score** | `INTERNAL_VAL` (4,493 samples) | 76,002.51 | **60,055.97** | **Random Forest** |
| **Official Test RMSE** | `EVAL_TEST` (100 engines) | **18.8279** | 19.0187 | Ridge Regression |
| **Official Test PHM Score** | `EVAL_TEST` (100 engines) | **781.21** | 1,306.84 | Ridge Regression |

## Analysis of Results
1. **Validation Performance:** Random Forest outperformed Ridge on internal validation (RMSE $19.54$ vs $20.14$, PHM Score $60,055$ vs $76,002$), capturing subtle non-linear degradation in HPC discharge pressure and bypass ratios.
2. **Selection Outcome:** In accordance with the predefined selection rule, **Random Forest Regressor** (`rul-randomforest-v1.0.0`) was designated as the active serving model (`is_active = True`).
3. **Generalization to Official Test:** On official test engines evaluated at their final censored cycle, Ridge exhibited tighter conservatism (RMSE $18.83$, PHM $781.21$) while Random Forest achieved RMSE $19.02$ and PHM $1,306.84$. Both models demonstrate solid, competitive baseline accuracy without hyperparameter overfitting or test-set leakage.

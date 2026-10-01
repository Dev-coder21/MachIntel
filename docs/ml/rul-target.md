# RUL Target Formulation & Piecewise Clipping

## Theoretical Formulation
In turbofan prognostic health management, initial engine operation exhibits negligible detectable degradation while components operate within design manufacturing tolerances. Measurable high-pressure compressor (HPC) and turbine wear develops gradually only after an initial operating period.

Following the standard literature for the NASA C-MAPSS benchmark (e.g. Heimes 2008, Ramasso 2014, Zheng 2017), the target Remaining Useful Life (RUL) is formulated as a piecewise-linear function clipped at an upper threshold $RUL_{max} = 125$ cycles:

$$RUL^*(t) = \min(RUL_{max}, T_{fail} - t)$$

Where:
- $t$: Current observed cycle ($1 \le t \le T_{fail}$).
- $T_{fail}$: Engine failure cycle (for run-to-failure training engines).
- $RUL_{max} = 125$: Maximum modeled remaining useful life cap.

```
Ground Truth RUL
       ^
 125 --+--------------------\
       |                     \
       |                      \
       |                       \
       |                        \
   0 --+-------------------------\-----> Observation Cycle (t)
       0                         T_fail
```

## Physical Rationale
1. **Nominal Operating Regime ($T_{fail} - t > 125$):** Sensor measurements reflect baseline operating conditions without significant thermal or mechanical degradation signatures. Attempting linear regression to early cycles (e.g. 250 or 300 cycles) forces the model to associate normal operating noise with degradation, degrading predictive accuracy.
2. **Degradation Regime ($T_{fail} - t \le 125$):** Degradation trajectories in sensor temperatures, pressures, and flow ratios accelerate monotonically towards failure. Linear remaining life tracking in this regime provides stable gradient signals for optimization.

## Bounds & Clamping Safeguards
- **Displayed Remaining Useful Life:** Model output is constrained to $\hat{RUL} \ge 0.0$ via $\max(0.0, \hat{y})$. Negative predicted cycles are strictly prohibited.
- **Official Test Engines:** For test engines censored at observation cycle $T_{obs}$, official test ground truth $y_{true}$ from `RUL_FD001.txt` is also bounded: $y_{eval} = \min(125, y_{true})$.

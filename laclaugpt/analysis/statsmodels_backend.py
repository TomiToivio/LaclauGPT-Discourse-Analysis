"""statsmodels backend: traditional statistical inference on REVIEWED
corpus-level results.

Input is a tabular analytical dataset built from human-reviewed,
corpus-level results — never raw LLM outputs. Statistical inference
stays distinct from theoretical interpretation: statsmodels reports
coefficients, intervals and diagnostics; whether a pattern is a
discourse-level claim remains Laclaudian analysis with evidence.
"""
from __future__ import annotations

from typing import Any

from laclaugpt.analysis import BackendUnavailable

_BACKEND = "statsmodels"


def is_available() -> bool:
    try:
        import statsmodels  # noqa: F401
        return True
    except ImportError:
        return False


def _version() -> str:
    try:
        import importlib.metadata
        return importlib.metadata.version("statsmodels")
    except Exception:
        return ""


def fit(dataset: Any, *, formula: str | None = None, method: str = "ols",
        **options: Any) -> dict[str, Any]:
    """Fit one statistical model.

    dataset: pandas.DataFrame of reviewed corpus-level rows.
    formula: optional patsy formula (e.g.
        "signifier_prevalence ~ period + formation")
    method: ols | logit | glm | arima (arima uses options endog/order)
    Returns coefficients, p-values, confidence intervals and diagnostics
    as plain JSON-safe structures; never theoretical claims.
    """
    if not is_available():
        raise BackendUnavailable("statsmodels is not installed")
    import pandas as pd
    import statsmodels.formula.api as smf
    import statsmodels.api as sm

    if not isinstance(dataset, pd.DataFrame):
        raise TypeError("dataset must be a pandas.DataFrame of reviewed results")
    if method == "arima":
        endog = options.pop("endog", None)
        if endog is None:
            raise ValueError("arima requires endog (series) in options")
        order = tuple(options.pop("order", (1, 1, 1)))
        trained = sm.tsa.ARIMA(dataset[endog] if endog in dataset.columns
                               else endog, order=order).fit()
    elif not formula:
        raise ValueError(f"method {method!r} requires a patsy formula")
    elif method == "ols":
        trained = smf.ols(formula, data=dataset).fit(**options)
    elif method == "logit":
        trained = smf.logit(formula, data=dataset).fit(**options)
    elif method == "glm":
        family = options.pop("family", None)
        trained = smf.glm(formula, data=dataset, family=family).fit(**options)
    else:
        raise ValueError(f"unknown statsmodels method: {method}")

    conf = trained.conf_int()
    params = trained.params
    pvalues = trained.pvalues
    return {
        "method": method, "formula": formula,
        "statsmodels_version": _version(),
        "n_observations": int(getattr(trained, "nobs", len(dataset))),
        "coefficients": {name: float(params[name]) for name in params.index},
        "p_values": {name: float(pvalues[name]) for name in pvalues.index},
        "confidence_intervals": {
            name: [float(conf.loc[name, 0]), float(conf.loc[name, 1])]
            for name in conf.index
        },
        "diagnostics": {
            "aic": float(trained.aic) if hasattr(trained, "aic") else None,
            "bic": float(trained.bic) if hasattr(trained, "bic") else None,
            "rsquared": (float(trained.rsquared)
                         if hasattr(trained, "rsquared") else None),
        },
        "summary": str(trained.summary()),
        "boundary_note": ("statistical inference on reviewed corpus-level "
                          "results; theoretical interpretation stays with "
                          "the discourse analysis"),
    }


def ttest(group_a: list[float], group_b: list[float], *,
          test: str = "ttest_ind") -> dict[str, Any]:
    """Two-group statistical test (e.g. frontier prevalence before/after
    an event, actor-group articulation pattern differences)."""
    if not is_available():
        raise BackendUnavailable("statsmodels is not installed")
    import statsmodels.stats.weightstats as smws
    if test == "ttest_ind":
        statistic, pvalue, df = smws.ttest_ind(group_a, group_b, usevar="unequal")
        return {"test": test, "statistic": float(statistic),
                "p_value": float(pvalue), "degrees_of_freedom": float(df),
                "n_a": len(group_a), "n_b": len(group_b),
                "statsmodels_version": _version()}
    raise ValueError(f"unknown test: {test}")
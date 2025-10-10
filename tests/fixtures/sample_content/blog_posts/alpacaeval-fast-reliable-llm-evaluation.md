---
title: AlpacaEval: Fast and Reliable LLM-Based Evaluation
author: Unknown
date: Unknown
source_url: https://tatsu-lab.github.io/alpaca_eval/
category: blog_post
tags: ['LLM', 'evaluation', 'community contributions', 'AI safety', 'natural language processing']
found_in: reading_07_llm_benchmarks_evaluation.md
---

# AlpacaEval: Fast and Reliable LLM-Based Evaluation

**Author:** Unknown  
**Date:** Unknown  
**Source:** [https://tatsu-lab.github.io/alpaca_eval/](https://tatsu-lab.github.io/alpaca_eval/)

## Summary

AlpacaEval is an LLM-based automatic evaluation tool that efficiently assesses model performance on user instructions. It utilizes the AlpacaFarm evaluation set and offers high agreement with human annotations, while also inviting community contributions for new models and evaluators.

---

# AlpacaEval: Fast and Reliable LLM-Based Evaluation

[AlpacaEval](https://github.com/tatsu-lab/alpaca_eval) is an LLM-based automatic evaluation that is fast, cheap, and reliable. It is based on the [AlpacaFarm](https://crfm.stanford.edu/2023/05/22/alpaca-farm.html) evaluation set, which tests the ability of models to follow general user instructions.

These responses are then compared to reference responses (Davinci003 for AlpacaEval, GPT-4 Preview for AlpacaEval 2.0) by the provided GPT-4 based auto-annotators, resulting in the win rates presented above. AlpacaEval displays a high agreement rate with ground truth human annotations, and leaderboard rankings on AlpacaEval are very correlated with leaderboard rankings based on human annotators. Please see our [documentation](https://github.com/tatsu-lab/alpaca_eval#analysis) for more details on our analysis.

## Community Contributions

We welcome new model contributions to the leaderboard from the community! To do so, please follow the steps in the [contributions section](https://github.com/tatsu-lab/alpaca_eval#contributing). Specifically, you'll need to run the model on the evaluation set, auto-annotate the outputs, and submit a PR with the model config and leaderboard results. We've also set up a [Discord](https://discord.gg/GJMxJSVZZM) for community support and discussion.

We also welcome contributions for new evaluators or new eval sets! For making new evaluators, we release our ground-truth [human annotations](https://github.com/tatsu-lab/alpaca_eval#data-release) and [comparison metrics](https://github.com/tatsu-lab/alpaca_eval#analyzing-an-evaluator). We also release a [rough guide](https://github.com/tatsu-lab/alpaca_eval#analyzing-an-eval-set) to follow for making new eval sets. We specifically encourage contributions for harder instructions distributions and for safety testing of LLMs.

## Limitations of AlpacaEval

While AlpacaEval provides a useful comparison of model capabilities in following instructions, it is not a comprehensive or gold-standard evaluation of model abilities. For one, as detailed in the [AlpacaFarm paper](https://arxiv.org/abs/2305.14387), the auto annotator win rates are correlated with length. Though human annotations also display this bias, it is unclear if more verbose answers add utility in downstream tasks. Additionally, the AlpacaFarm eval set, though diverse, consists mainly of simple instructions. We encourage the community to contribute new, more complex eval sets, such as for tool use. Finally, AlpacaEval does not evaluate the safety of any of the models.
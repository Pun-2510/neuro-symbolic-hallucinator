"""Synthetic Dataset Generator for Citation Integrity Evaluation.

Generates 200 labeled citations:
- 100 REAL: Famous papers (NeurIPS, ACL, Nature, etc.) + ACL papers
- 70 HALLUCINATED: Fake authors, future years, fake DOIs, fake venues
- 30 METADATA_ERROR: Real papers with wrong year/author/title

Usage:
    python -m evaluation.synthetic_dataset

Output:
    evaluation/ground_truth.json
    evaluation/ground_truth_stats.json
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
import uuid

# =============================================================================
# REAL PAPERS - Famous papers in AI/ML/NLP
# =============================================================================

FAMOUS_REAL_PAPERS = [
    # Attention & Transformers
    {"authors": "Vaswani et al.", "year": 2017, "title": "Attention Is All You Need", "venue": "NeurIPS", "doi": "10.48550/arXiv.1706.03762"},
    {"authors": "Devlin et al.", "year": 2019, "title": "BERT: Pre-training of Deep Bidirectional Transformers", "venue": "ACL", "doi": "10.18653/v1/N19-1423"},
    {"authors": "Radford et al.", "year": 2019, "title": "Language Models are Unsupervised Multitask Learners", "venue": "OpenAI Technical Report", "doi": ""},
    {"authors": "Brown et al.", "year": 2020, "title": "Language Models are Few-Shot Learners", "venue": "NeurIPS", "doi": "10.48550/arXiv.2005.14165"},
    {"authors": "Kaplan et al.", "year": 2020, "title": "Scaling Laws for Neural Language Models", "venue": "arXiv", "doi": "10.48550/arXiv.2001.08361"},
    {"authors": "Rae et al.", "year": 2021, "title": "Scaling Language Models: Methods, Analysis & Insights", "venue": "arXiv", "doi": "10.48550/arXiv.2112.11446"},
    {"authors": "Chowdhery et al.", "year": 2022, "title": "PaLM: Scaling Language Modeling with Pathways", "venue": "arXiv", "doi": "10.48550/arXiv.2204.02311"},
    {"authors": "Touvron et al.", "year": 2023, "title": "LLaMA: Open and Efficient Foundation Language Models", "venue": "Meta AI Research", "doi": "10.48550/arXiv.2302.13971"},

    # BERT & Pretraining
    {"authors": "Liu et al.", "year": 2019, "title": "RoBERTa: A Robustly Optimized BERT Pretraining Approach", "venue": "arXiv", "doi": "10.48550/arXiv.1907.11692"},
    {"authors": "Lan et al.", "year": 2020, "title": "ALBERT: A Lite BERT for Self-supervised Learning", "venue": "ICLR", "doi": "10.48550/arXiv.1909.11942"},
    {"authors": "Clark et al.", "year": 2020, "title": "ELECTRA: Pre-training Text Encoders as Discriminators", "venue": "ICLR", "doi": "10.48550/arXiv.2003.10555"},
    {"authors": "Sanh et al.", "year": 2019, "title": "DistilBERT, a Distilled Version of BERT", "venue": "NeurIPS Workshop", "doi": "10.48550/arXiv.1910.01108"},

    # GPT Series
    {"authors": "Radford and Narasimhan", "year": 2018, "title": "Improving Language Understanding by Generative Pre-Training", "venue": "OpenAI Technical Report", "doi": ""},
    {"authors": "OpenAI", "year": 2023, "title": "GPT-4 Technical Report", "venue": "OpenAI", "doi": ""},
    {"authors": "Anthropic", "year": 2024, "title": "The Claude 3 Model Family", "venue": "Anthropic Technical Report", "doi": ""},

    # NLP Fundamentals
    {"authors": "Mikolov et al.", "year": 2013, "title": "Distributed Representations of Words and Phrases", "venue": "NeurIPS", "doi": ""},
    {"authors": "Pennington et al.", "year": 2014, "title": "GloVe: Global Vectors for Word Representation", "venue": "EMNLP", "doi": "10.3115/v1/D14-1162"},
    {"authors": "Peters et al.", "year": 2018, "title": "Deep Contextualized Word Representations", "venue": "NAACL", "doi": "10.18653/v1/N18-1202"},
    {"authors": "Devlin and Chang", "year": 2018, "title": "Open Source Release of BERT", "venue": "Google AI Blog", "doi": ""},

    # Seq2Seq & Attention
    {"authors": "Bahdanau et al.", "year": 2014, "title": "Neural Machine Translation by Jointly Learning to Align", "venue": "ICLR", "doi": "10.48550/arXiv.1409.0473"},
    {"authors": "Luong et al.", "year": 2015, "title": "Effective Approaches to Attention-based Neural Machine Translation", "venue": "EMNLP", "doi": "10.18653/v1/D15-1166"},
    {"authors": "Sutskever et al.", "year": 2014, "title": "Sequence to Sequence Learning with Neural Networks", "venue": "NeurIPS", "doi": ""},
    {"authors": "Cho et al.", "year": 2014, "title": "Learning Phrase Representations using RNN Encoder-Decoder", "venue": "EMNLP", "doi": "10.3115/v1/D14-1179"},

    # Machine Translation
    {"authors": "Sennrich et al.", "year": 2016, "title": "Neural Machine Translation of Rare Words with Subword Units", "venue": "ACL", "doi": "10.18653/v1/P16-1162"},
    {"authors": "Johnson et al.", "year": 2017, "title": "Google's Multilingual Neural Machine Translation System", "venue": "ACL", "doi": "10.18653/v1/P17-1009"},
    {"authors": "Edunov et al.", "year": 2018, "title": "Understanding Back-Translation at Scale", "venue": "EMNLP", "doi": "10.18653/v1/D18-1045"},

    # Computer Vision + Transformers
    {"authors": "He et al.", "year": 2016, "title": "Deep Residual Learning for Image Recognition", "venue": "CVPR", "doi": "10.1109/CVPR.2016.90"},
    {"authors": "Dosovitskiy et al.", "year": 2021, "title": "An Image is Worth 16x16 Words: Transformers for Image Recognition", "venue": "ICLR", "doi": "10.48550/arXiv.2010.11929"},
    {"authors": "Liu et al.", "year": 2021, "title": "Swin Transformer: Hierarchical Vision Transformer", "venue": "ICCV", "doi": "10.1109/ICCV48922.2021.00986"},

    # GANs & Generation
    {"authors": "Goodfellow et al.", "year": 2014, "title": "Generative Adversarial Networks", "venue": "NeurIPS", "doi": ""},
    {"authors": "Radford et al.", "year": 2016, "title": "Unsupervised Representation Learning with Deep Convolutional GANs", "venue": "ICLR", "doi": "10.48550/arXiv.1511.06434"},
    {"authors": "Karras et al.", "year": 2019, "title": "A Style-Based Generator Architecture for GANs", "venue": "CVPR", "doi": "10.1109/CVPR.2019.00409"},
    {"authors": "Brock et al.", "year": 2019, "title": "Large Scale GAN Training for High Fidelity Image Synthesis", "venue": "ICLR", "doi": "10.48550/arXiv.1809.11096"},

    # Reinforcement Learning
    {"authors": "Mnih et al.", "year": 2013, "title": "Playing Atari with Deep Reinforcement Learning", "venue": "arXiv", "doi": "10.48550/arXiv.1312.5602"},
    {"authors": "Mnih et al.", "year": 2015, "title": "Human-level Control through Deep Reinforcement Learning", "venue": "Nature", "doi": "10.1038/nature14236"},
    {"authors": "Silver et al.", "year": 2016, "title": "Mastering the Game of Go with Deep Neural Networks", "venue": "Nature", "doi": "10.1038/nature16961"},
    {"authors": "Silver et al.", "year": 2017, "title": "Mastering the Game of Go without Human Knowledge", "venue": "Nature", "doi": "10.1038/nature24270"},
    {"authors": "OpenAI et al.", "year": 2019, "title": "OpenAI Five Defeats World Champion Dota 2 Team", "venue": "arXiv", "doi": "10.48550/arXiv.1912.06680"},

    # LLM & Prompting
    {"authors": "Wei et al.", "year": 2022, "title": "Chain-of-Thought Prompting Elicits Reasoning", "venue": "NeurIPS", "doi": "10.48550/arXiv.2201.11903"},
    {"authors": "Kojima et al.", "year": 2022, "title": "Large Language Models are Zero-Shot Reasoners", "venue": "NeurIPS", "doi": "10.48550/arXiv.2205.11916"},
    {"authors": "Wang et al.", "year": 2022, "title": "Self-Consistency Improves Chain of Thought Reasoning", "venue": "ICLR", "doi": "10.48550/arXiv.2203.11171"},
    {"authors": "Yao et al.", "year": 2023, "title": "Tree of Thoughts: Deliberate Problem Solving with Large Models", "venue": "NeurIPS", "doi": "10.48550/arXiv.2305.10601"},

    # Retrieval & RAG
    {"authors": "Karpukhin et al.", "year": 2020, "title": "Dense Passage Retrieval for Open-Domain Question Answering", "venue": "EMNLP", "doi": "10.18653/v1/2020.emnlp-main.550"},
    {"authors": "Lewis et al.", "year": 2020, "title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP", "venue": "NeurIPS", "doi": "10.48550/arXiv.2005.11401"},
    {"authors": "Guu et al.", "year": 2020, "title": "REALM: Retrieval-Augmented Language Model Pre-Training", "venue": "ICML", "doi": "10.48550/arXiv.2002.08909"},

    # Knowledge Graphs
    {"authors": "Wang et al.", "year": 2017, "title": "Knowledge Graph Embedding: A Survey of Approaches", "venue": "IEEE TKDE", "doi": "10.1109/TKDE.2017.2754499"},
    {"authors": "Bordes et al.", "year": 2013, "title": "Translating Embeddings for Modeling Multi-relational Data", "venue": "NeurIPS", "doi": ""},

    # Few-Shot & Meta-Learning
    {"authors": "Finn et al.", "year": 2017, "title": "Model-Agnostic Meta-Learning for Fast Adaptation", "venue": "ICML", "doi": "10.48550/arXiv.1703.03400"},
    {"authors": "Snell et al.", "year": 2017, "title": "Prototypical Networks for Few-shot Learning", "venue": "NeurIPS", "doi": ""},

    # Optimization
    {"authors": "Kingma and Ba", "year": 2014, "title": "Adam: A Method for Stochastic Optimization", "venue": "ICLR", "doi": "10.48550/arXiv.1412.6980"},
    {"authors": "Loshchilov and Hutter", "year": 2019, "title": "Decoupled Weight Decay Regularization", "venue": "ICLR", "doi": "10.48550/arXiv.1711.05101"},

    # Normalization & Regularization
    {"authors": "Ioffe and Szegedy", "year": 2015, "title": "Batch Normalization: Accelerating Deep Network Training", "venue": "ICML", "doi": "10.48550/arXiv.1502.03167"},
    {"authors": "Ba et al.", "year": 2016, "title": "Layer Normalization", "venue": "arXiv", "doi": "10.48550/arXiv.1607.06450"},
    {"authors": "Hinton et al.", "year": 2015, "title": "Distilling the Knowledge in a Neural Network", "venue": "NeurIPS Workshop", "doi": "10.48550/arXiv.1503.02531"},

    # Self-Supervised Learning
    {"authors": "Chen et al.", "year": 2020, "title": "A Simple Framework for Contrastive Learning of Visual Representations", "venue": "ICML", "doi": "10.48550/arXiv.2002.05709"},
    {"authors": "Grill et al.", "year": 2020, "title": "Bootstrap Your Own Latent: A New Approach to Self-Supervised Learning", "venue": "NeurIPS", "doi": "10.48550/arXiv.2006.07733"},

    # Multi-Modality
    {"authors": "Radford et al.", "year": 2021, "title": "Learning Transferable Visual Models From Natural Language Supervision", "venue": "ICML", "doi": "10.48550/arXiv.2103.00020"},
    {"authors": "Alayrac et al.", "year": 2022, "title": "Flamingo: a Visual Language Model for Few-Shot Learning", "venue": "NeurIPS", "doi": "10.48550/arXiv.2204.14198"},

    # Sentiment & Classification
    {"authors": "Socher et al.", "year": 2013, "title": "Recursive Deep Models for Semantic Compositionality", "venue": "EMNLP", "doi": "10.3115/v1/D13-1170"},
    {"authors": "Kim", "year": 2014, "title": "Convolutional Neural Networks for Sentence Classification", "venue": "EMNLP", "doi": "10.3115/v1/D14-1181"},

    # Question Answering
    {"authors": "Rajpurkar et al.", "year": 2016, "title": "SQuAD: 100,000+ Questions for Machine Comprehension of Text", "venue": "EMNLP", "doi": "10.18653/v1/D16-1264"},
    {"authors": "Joshi et al.", "year": 2017, "title": "TriviaQA: A Large Scale Dataset for Reading Comprehension", "venue": "ACL", "doi": "10.18653/v1/P17-1147"},

    # Summarization
    {"authors": "Lewis et al.", "year": 2019, "title": "BART: Denoising Sequence-to-Sequence Pre-training", "venue": "ACL", "doi": "10.18653/v1/2020.acl-main.703"},
    {"authors": "Zhang et al.", "year": 2020, "title": "PEBUG: A Large-Scale Dialogue Generative Pre-Training", "venue": "TACL", "doi": ""},

    # Attention Variants
    {"authors": "Shen et al.", "year": 2018, "title": "Bi-directional Block Self-Attention for Fast and Memory-Efficient", "venue": "ICLR", "doi": "10.48550/arXiv.1805.08328"},
    {"authors": "Zaheer et al.", "year": 2020, "title": "Big Bird: Transformers for Longer Sequences", "venue": "NeurIPS", "doi": "10.48550/arXiv.2007.14062"},

    # Graph Neural Networks
    {"authors": "Kipf and Welling", "year": 2017, "title": "Semi-Supervised Classification with Graph Convolutional Networks", "venue": "ICLR", "doi": "10.48550/arXiv.1609.02907"},
    {"authors": "Velickovic et al.", "year": 2018, "title": "Graph Attention Networks", "venue": "ICLR", "doi": "10.48550/arXiv.1710.10903"},

    # Efficiency & Distillation
    {"authors": "Jiao et al.", "year": 2020, "title": "TinyBERT: Distilling BERT for Natural Language Understanding", "venue": "EMNLP", "doi": "10.18653/v1/2020.emnlp-main.363"},
    {"authors": "Sun et al.", "year": 2020, "title": "MobileBERT: a Compact Task-Agnostic BERT", "venue": "ACL", "doi": "10.18653/v1/2020.acl-main.195"},

    # Uncertainty & Calibration
    {"authors": "Guo et al.", "year": 2017, "title": "On Calibration of Modern Neural Networks", "venue": "ICML", "doi": "10.48550/arXiv.1706.04599"},
    {"authors": "Lakshminarayanan et al.", "year": 2017, "title": "Simple and Scalable Predictive Uncertainty Estimation", "venue": "NeurIPS", "doi": ""},
]

# =============================================================================
# ACL PAPERS - Real papers from ACL Anthology (representative sample)
# =============================================================================

ACL_REAL_PAPERS = [
    {"authors": "Wang et al.", "year": 2018, "title": "Glue: A Multi-Task Benchmark", "venue": "ICLR", "doi": "10.48550/arXiv.1804.07461"},
    {"authors": "Conneau et al.", "year": 2017, "title": "Supervised Learning of Universal Sentence Representations", "venue": "EMNLP", "doi": "10.18653/v1/D17-1070"},
    {"authors": "Subramanian et al.", "year": 2018, "title": "Learning General Purpose Distributed Sentence Representations", "venue": "ICML", "doi": "10.48550/arXiv.1803.02810"},
    {"authors": "Cer et al.", "year": 2018, "title": "Universal Sentence Encoder", "venue": "NAACL Workshop", "doi": "10.18653/v1/W18-2608"},
    {"authors": "Hill et al.", "year": 2016, "title": "Learning Distributed Representations of Sentences", "venue": "NAACL", "doi": "10.18653/v1/N16-1082"},
    {"authors": "Arora et al.", "year": 2017, "title": "A Simple but Tough-to-Beat Baseline for Sentence Embeddings", "venue": "ICLR", "doi": ""},
    {"authors": "Bojanowski et al.", "year": 2017, "title": "Enriching Word Vectors with Subword Information", "venue": "TACL", "doi": "10.1162/tacl_a_00051"},
    {"authors": "Joulin et al.", "year": 2017, "title": "Bag of Tricks for Efficient Text Classification", "venue": "EACL", "doi": "10.18653/v1/E17-2068"},
    {"authors": "Le and Mikolov", "year": 2014, "title": "Distributed Representations of Sentences and Documents", "venue": "ICML", "doi": "10.48550/arXiv.1405.4053"},
    {"authors": "Kiros et al.", "year": 2015, "title": "Skip-Thought Vectors", "venue": "NeurIPS", "doi": ""},
    {"authors": "Melamud et al.", "year": 2016, "title": "context2vec: Learning Generic Context Embedding", "venue": "CoNLL", "doi": "10.18653/v1/K16-1006"},
    {"authors": "McCann et al.", "year": 2017, "title": "Learned in Translation: Contextualized Word Vectors", "venue": "NeurIPS", "doi": ""},
    {"authors": "Choi et al.", "year": 2018, "title": "Decomposing Question and Context", "venue": "TACL", "doi": ""},
    {"authors": "Seo et al.", "year": 2017, "title": "Bidirectional Attention Flow for Machine Comprehension", "venue": "ICLR", "doi": "10.48550/arXiv.1611.01603"},
    {"authors": "Clark and Manning", "year": 2016, "title": "Deep Reinforcement Learning for Mention Ranking", "venue": "NAACL", "doi": "10.18653/v1/N16-1175"},
    {"authors": "Parikh et al.", "year": 2016, "title": "A Decomposable Attention Model for Natural Language Inference", "venue": "EMNLP", "doi": "10.18653/v1/D16-1244"},
    {"authors": "Rocktäschel et al.", "year": 2016, "title": "Reasoning about Entailment with Neural Attention", "venue": "ICLR", "doi": "10.48550/arXiv.1509.06664"},
    {"authors": "Mou et al.", "year": 2016, "title": "Natural Language Inference by Tree-Based Convolution", "venue": "EMNLP Workshop", "doi": "10.18653/v1/W16-2922"},
    {"authors": "Bowman et al.", "year": 2015, "title": "A Large Annotated Corpus for Learning Natural Language Inference", "venue": "EMNLP", "doi": "10.18653/v1/D15-1075"},
    {"authors": "Williams et al.", "year": 2018, "title": "A Broad-Coverage Challenge Corpus for Sentence Understanding", "venue": "NAACL", "doi": "10.18653/v1/N18-1201"},
    {"authors": "Dagan et al.", "year": 2006, "title": "The PASCAL Recognising Textual Entailment Challenge", "venue": "Machine Learning Challenges", "doi": "10.1007/11736790_3"},
    {"authors": "Bar-Haim et al.", "year": 2006, "title": "The Second PASCAL Recognizing Textual Entailment Challenge", "venue": "PASCAL", "doi": ""},
    {"authors": "Giampiccolo et al.", "year": 2007, "title": "The Third PASCAL Recognizing Textual Entailment Challenge", "venue": "ACL Workshop", "doi": "10.3115/1611628.1611637"},
    {"authors": "Bentivogli et al.", "year": 2009, "title": "The Fifth PASCAL Recognizing Textual Entailment Challenge", "venue": "TAC", "doi": ""},
    {"authors": "Levy et al.", "year": 2015, "title": "Improving Distributional Similarity with Lessons Learned from Word Embeddings", "venue": "TACL", "doi": "10.1162/tacl_a_00134"},
    {"authors": "Schnabel et al.", "year": 2015, "title": "Evaluation methods for unsupervised word embeddings", "venue": "EMNLP", "doi": "10.18653/v1/D15-1036"},
    {"authors": "Faruqui et al.", "title": "Retrofitting Word Vectors to Semantic Lexicons", "year": 2015, "venue": "NAACL", "doi": "10.18653/v1/N15-1184"},
    {"authors": "Mrkšić et al.", "year": 2016, "title": "Counter-fitting Word Vectors to Linguistic Constraints", "venue": "NAACL", "doi": "10.18653/v1/N16-1018"},
    {"authors": "Wieting et al.", "year": 2016, "title": "Towards Universal Paraphrastic Sentence Embeddings", "venue": "ICLR", "doi": "10.48550/arXiv.1511.08198"},
    {"authors": "Wieting and Gimpel", "year": 2017, "title": "PNGR: ParaNMT-50M: Pushing the Limits of Paraphrastic Sentence Embeddings", "venue": "EMNLP", "doi": "10.18653/v1/D17-1132"},
]


# =============================================================================
# HALLUCINATED CITATIONS - Fake authors, future years, fake DOIs
# =============================================================================

FAKE_AUTHORS = [
    "NonExistent Researcher", "FakeAuthor et al.", "MysteryPaper",
    "Invented Scientist", "Imaginary Scholar", "Phantom Author",
    "Unknown Research", "Fabricated Author", "NonExistent et al.",
    "MadeUp Name", "Fictional Scholar", "Inexistent Author",
    "Bogus Research", "Phony Paper", "Counterfeit Scholar",
    "Synthetic Scientist", "Artificial Author", "Hypothetical Research",
    "Imagined Paper", "Constructed Scholar", "Manufactured Author",
]

FAKE_TITLES = [
    "A Novel Approach to Fake Research", "The Non-Existent Method",
    "Revolutionary Discovery in Pseudoscience", "Groundbreaking False Findings",
    "The Art of Fabricating Research", "An Impossible Study of Nothing",
    "Quantum Dreams and Fake Realities", "The Study of Undiscovered Discoveries",
    "Advanced Techniques in Imaginary Science", "The Complete Guide to Fake Data",
]

FAKE_VENUES = [
    "Journal of Non-Existent Research", "International Conference on Made-Up Science",
    "Proceedings of the Imaginary Academy", "Review of Pseudoscientific Studies",
    "Annals of Fake Science", "Frontiers in Non-Existent Research",
    "Transactions on Invented Knowledge", "Advances in Counterfeit Science",
]

# Valid DOI prefixes (random)
VALID_DOI_PREFIXES = ["10.1000", "10.1038", "10.1126", "10.48550", "10.18653", "10.1145"]
# Fake DOI prefixes
FAKE_DOI_PREFIXES = ["10.9999", "10.fake", "10.1234", "10.abric", "10.invalid", "10.null"]


@dataclass
class CitationEntry:
    """A citation entry with ground truth label."""
    citation_id: str
    citation_raw: str
    citation_formatted: str
    ground_truth: str  # REAL | HALLUCINATED | METADATA_ERROR
    source: str  # Famous | ACL | Synthetic
    original_paper: Optional[dict] = None  # For REAL/METADATA_ERROR types

    def to_dict(self) -> dict:
        return asdict(self)


class SyntheticDatasetGenerator:
    """Generate synthetic dataset with ground truth labels."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.all_real_papers = FAMOUS_REAL_PAPERS + ACL_REAL_PAPERS
        self.rng.shuffle(self.all_real_papers)

    def format_citation_apa(self, authors: str, year: int, title: str, venue: str) -> str:
        """Format citation in APA-like style."""
        return f"{authors} ({year}). {title}. {venue}."

    def format_citation_author_year(self, authors: str, year: int) -> str:
        """Format simple author-year citation."""
        return f"{authors} ({year})"

    def generate_real_citations(self, n: int = 100) -> list[CitationEntry]:
        """Generate REAL citations from known papers."""
        papers = self.all_real_papers[:n]
        entries = []

        for i, paper in enumerate(papers):
            paper_id = f"REAL_{i+1:03d}"

            # Format: simple author-year style (common in-text citation)
            citation_raw = self.format_citation_author_year(
                paper["authors"], paper["year"]
            )

            citation_formatted = self.format_citation_apa(
                paper["authors"], paper["year"],
                paper["title"], paper["venue"]
            )

            entries.append(CitationEntry(
                citation_id=paper_id,
                citation_raw=citation_raw,
                citation_formatted=citation_formatted,
                ground_truth="REAL",
                source="Famous" if i < len(FAMOUS_REAL_PAPERS) else "ACL",
                original_paper=paper
            ))

        return entries

    def generate_hallucinated_citations(self, n: int = 70) -> list[CitationEntry]:
        """Generate HALLUCINATED citations."""
        entries = []

        hallucination_types = [
            ("fake_author", 0.35),      # 35% - fake authors
            ("future_year", 0.25),      # 25% - future years
            ("fake_doi", 0.20),         # 20% - fake DOIs
            ("fake_venue", 0.10),       # 10% - fake venues
            ("fake_title", 0.10),       # 10% - fake titles
        ]

        for i in range(n):
            # Select hallucination type
            rand = self.rng.random()
            cumulative = 0
            selected_type = "fake_author"

            for htype, prob in hallucination_types:
                cumulative += prob
                if rand <= cumulative:
                    selected_type = htype
                    break

            citation_id = f"HALLU_{i+1:03d}"

            if selected_type == "fake_author":
                authors = self.rng.choice(FAKE_AUTHORS)
                year = self.rng.randint(2015, 2024)
                title = self.rng.choice(FAKE_TITLES)
                citation_raw = self.format_citation_author_year(authors, year)
                citation_formatted = self.format_citation_apa(
                    authors, year, title,
                    self.rng.choice(FAKE_VENUES)
                )

            elif selected_type == "future_year":
                # Pick a real author name
                real_paper = self.rng.choice(FAMOUS_REAL_PAPERS)
                # But with future year
                year = self.rng.randint(2050, 2100)
                citation_raw = self.format_citation_author_year(
                    real_paper["authors"], year
                )
                citation_formatted = self.format_citation_apa(
                    real_paper["authors"], year,
                    real_paper["title"], real_paper["venue"]
                )

            elif selected_type == "fake_doi":
                authors = self.rng.choice(FAKE_AUTHORS)
                year = self.rng.randint(2015, 2024)
                # Generate fake DOI
                prefix = self.rng.choice(FAKE_DOI_PREFIXES)
                suffix = f"{self.rng.randint(1000, 9999)}.{self.rng.randint(100, 999)}"
                fake_doi = f"{prefix}.{suffix}"
                citation_raw = f"{authors} ({year}). DOI: {fake_doi}"
                citation_formatted = f"{authors} ({year}). Fake Paper Title. DOI: {fake_doi}."

            elif selected_type == "fake_venue":
                # Real authors but fake venue
                real_paper = self.rng.choice(FAMOUS_REAL_PAPERS)
                citation_raw = self.format_citation_author_year(
                    real_paper["authors"], real_paper["year"]
                )
                citation_formatted = self.format_citation_apa(
                    real_paper["authors"], real_paper["year"],
                    real_paper["title"],
                    self.rng.choice(FAKE_VENUES)
                )

            else:  # fake_title
                authors = self.rng.choice(FAKE_AUTHORS)
                year = self.rng.randint(2015, 2024)
                title = self.rng.choice(FAKE_TITLES)
                citation_raw = self.format_citation_author_year(authors, year)
                citation_formatted = self.format_citation_apa(
                    authors, year, title,
                    self.rng.choice(FAKE_VENUES)
                )

            entries.append(CitationEntry(
                citation_id=citation_id,
                citation_raw=citation_raw,
                citation_formatted=citation_formatted,
                ground_truth="HALLUCINATED",
                source=f"Synthetic_{selected_type}",
                original_paper=None
            ))

        return entries

    def generate_metadata_error_citations(self, n: int = 30) -> list[CitationEntry]:
        """Generate METADATA_ERROR citations (real papers with wrong metadata)."""
        entries = []
        papers = self.all_real_papers[:n]
        error_types = ["wrong_year", "wrong_author", "wrong_title"]

        for i, paper in enumerate(papers):
            paper_id = f"METAERR_{i+1:03d}"
            error_type = self.rng.choice(error_types)

            if error_type == "wrong_year":
                # Same author, different year
                wrong_year = paper["year"] + self.rng.randint(5, 15)
                citation_raw = self.format_citation_author_year(
                    paper["authors"], wrong_year
                )
                citation_formatted = self.format_citation_apa(
                    paper["authors"], wrong_year,
                    paper["title"], paper["venue"]
                )
            elif error_type == "wrong_author":
                # Wrong author (real-ish but wrong name), same year
                # Use similar but slightly different real author names
                original_author = paper["authors"].split(" et al.")[0].split(" and ")[0]
                # Common ML author names to confuse with
                similar_authors = [
                    "Wang", "Li", "Zhang", "Liu", "Chen", "Yang", "Huang",
                    "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
                    "Kim", "Park", "Lee", "Nguyen", "Tran",
                ]
                # Pick a different but realistic author
                different_author = self.rng.choice([a for a in similar_authors if a != original_author])
                wrong_author = f"{different_author} et al."
                citation_raw = self.format_citation_author_year(wrong_author, paper["year"])
                citation_formatted = self.format_citation_apa(
                    wrong_author, paper["year"],
                    paper["title"], paper["venue"]
                )
            else:  # wrong_title
                # Same author/year, wrong title
                citation_raw = self.format_citation_author_year(
                    paper["authors"], paper["year"]
                )
                citation_formatted = self.format_citation_apa(
                    paper["authors"], paper["year"],
                    self.rng.choice(FAKE_TITLES), paper["venue"]
                )

            entries.append(CitationEntry(
                citation_id=paper_id,
                citation_raw=citation_raw,
                citation_formatted=citation_formatted,
                ground_truth="METADATA_ERROR",
                source=f"Error_{error_type}",
                original_paper=paper
            ))

        return entries

    def generate_dataset(self, n_real: int = 100, n_hallu: int = 70, n_metaerr: int = 30) -> list[CitationEntry]:
        """Generate full dataset."""
        dataset = []
        dataset.extend(self.generate_real_citations(n_real))
        dataset.extend(self.generate_hallucinated_citations(n_hallu))
        dataset.extend(self.generate_metadata_error_citations(n_metaerr))

        # Shuffle to randomize order
        self.rng.shuffle(dataset)

        # Re-number after shuffle
        for i, entry in enumerate(dataset):
            entry.citation_id = f"eval_{i+1:04d}"

        return dataset

    def save_dataset(self, dataset: list[CitationEntry], output_dir: str = None) -> dict:
        """Save dataset to JSON files."""
        if output_dir is None:
            output_dir = Path(__file__).parent
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        # Convert to dict for JSON
        dataset_dict = [e.to_dict() for e in dataset]

        # Main dataset file
        dataset_path = output_dir / "ground_truth.json"
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset_dict, f, ensure_ascii=False, indent=2)

        # Statistics file
        stats = self.compute_stats(dataset)
        stats_path = output_dir / "ground_truth_stats.json"
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)

        print(f"Dataset saved to {dataset_path}")
        print(f"Statistics saved to {stats_path}")

        return {"dataset_path": str(dataset_path), "stats_path": str(stats_path)}

    def compute_stats(self, dataset: list[CitationEntry]) -> dict:
        """Compute dataset statistics."""
        stats = {
            "total": len(dataset),
            "by_label": {},
            "by_source": {},
            "hallucination_types": {},
        }

        for entry in dataset:
            # By label
            stats["by_label"][entry.ground_truth] = \
                stats["by_label"].get(entry.ground_truth, 0) + 1

            # By source
            if entry.source:
                stats["by_source"][entry.source] = \
                    stats["by_source"].get(entry.source, 0) + 1

            # Hallucination types
            if entry.ground_truth == "HALLUCINATED":
                htype = entry.source.replace("Synthetic_", "")
                stats["hallucination_types"][htype] = \
                    stats["hallucination_types"].get(htype, 0) + 1

        return stats


def main():
    """Generate the synthetic dataset."""
    print("=" * 60)
    print("SYNTHETIC DATASET GENERATOR FOR CITATION INTEGRITY EVALUATION")
    print("=" * 60)

    generator = SyntheticDatasetGenerator(seed=42)

    # Generate 200 samples: 100 REAL, 70 HALLUCINATED, 30 METADATA_ERROR
    dataset = generator.generate_dataset(
        n_real=100,
        n_hallu=70,
        n_metaerr=30
    )

    # Save
    paths = generator.save_dataset(dataset)

    # Print stats
    print("\n" + "=" * 60)
    print("DATASET GENERATED SUCCESSFULLY")
    print("=" * 60)
    print(f"Total samples: {len(dataset)}")
    print(f"  - REAL:            100")
    print(f"  - HALLUCINATED:     70")
    print(f"  - METADATA_ERROR:   30")
    print("\nSample entries:")
    for i, entry in enumerate(dataset[:5]):
        print(f"\n[{i+1}] {entry.citation_id}")
        print(f"    Raw: {entry.citation_raw}")
        print(f"    Label: {entry.ground_truth}")

    return paths


if __name__ == "__main__":
    main()

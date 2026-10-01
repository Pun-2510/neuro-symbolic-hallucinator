"""Tạo sample essay PDF với 10 citations để test pipeline.

Kịch bản:
- 4 citation types: APA in-text, numeric, IEEE, Vancouver
- 3 real papers: Vaswani 2017 (Attention), Devlin 2018 (BERT), He 2016 (ResNet)
- 3 fabricated papers: Hallucination 1, 2, 3
- 2 borderline: borderline_valid, questionable_doi
- Multiple references per citation (et al.)
- Mix of formats in reference list
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ESSAY_CONTENT = """Deep Learning for Natural Language Processing: A Comprehensive Survey

In recent years, deep learning has revolutionized natural language processing (NLP) with
breakthrough models that achieve state-of-the-art results across diverse tasks (Vaswani et al., 2017;
Devlin et al., 2018). The transformer architecture, introduced by Vaswani et al. (2017), has become
the foundation for modern NLP systems.

Self-attention mechanisms enable models to capture long-range dependencies in text (Vaswani et al.,
2017). The attention mechanism allows each token to attend to all other tokens in the sequence,
enabling parallel computation and improved training efficiency. This architectural innovation replaced
recurrent neural networks in many applications.

Bidirectional encoding through pre-training has shown remarkable effectiveness (Devlin et al., 2018).
BERT introduces a masked language modeling objective that enables deep bidirectional representations.
The model achieves new state-of-the-art results on eleven NLP tasks including question answering,
text classification, and named entity recognition (Devlin et al., 2018).

Convolutional neural networks have also proven effective for visual recognition tasks (He et al., 2016).
The residual learning framework addresses the degradation problem in very deep networks. This approach
enables training of networks with significantly greater depth, leading to improved accuracy on image
classification benchmarks (He et al., 2016).

However, concerns about hallucination in large language models have emerged as a critical challenge
(Xiao et al., 2023). These models sometimes generate factually incorrect content that appears
confident and coherent. Research into retrieval-augmented generation aims to mitigate this issue
by grounding model outputs in external knowledge bases (Zhang et al., 2023).

The field continues to evolve rapidly with new architectures and training paradigms (Brown et al.,
2020). Foundation models demonstrate emergent capabilities across diverse domains. Evaluation
methodologies must keep pace with these advances to ensure reliable assessment of model
capabilities (Kiela et al., 2021).

References

Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, L., &
    Polosukhin, I. (2017). Attention is all you need. Advances in Neural Information Processing
    Systems, 30, 5998-6008. https://doi.org/10.48550/arXiv.1706.03762

Devlin, J., Chang, M. W., Lee, K., & Toutanova, K. (2018). BERT: Pre-training of deep
    bidirectional transformers for language understanding. Proceedings of the 2019 Conference of
    the North American Chapter of the Association for Computational Linguistics, 4171-4186.
    https://doi.org/10.18653/v1/N19-1423

He, K., Zhang, X., Ren, S., & Sun, J. (2016). Deep residual learning for image recognition.
    Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition, 770-778.
    https://doi.org/10.1109/CVPR.2016.90

[4] Xiao, Y., Wang, J., & Lee, S. (2023). "Hallucination detection in large language models
    using semantic consistency," Journal of AI Safety, vol. 15, pp. 112-128, 2023.

Xiao Y. Hallucination in neural networks. Neural Computing Review. 2022;45:234-256.
https://doi.org/10.1234/ncr.2022.0456

Zhang, Q., Chen, M., & Park, J. (2023). Retrieval-augmented generation for knowledge-intensive
    NLP tasks. Technical Report TR-2023-01. Available at: https://example.com/rag-tech.pdf

Brown, T. B., Mann, B., Ryder, N., Subbiah, M., Kaplan, J., Dhariwal, P., ... & Amodei, D.
    (2020). Language models are few-shot learners. Advances in Neural Information Processing
    Systems, 33, 1877-1901.

Kiela, D., Bartolo, M., Jiang, Y., Nie, F., Warstadt, A., Conneau, A., ... & Bowman, S. (2021).
    Dynabench: Rethinking benchmarking in NLP. Findings of ACL-IJCNLP 2021, 4144-4163.

Zhang, X., & Li, H. (2023). On the ethics of artificial intelligence systems. Journal of
    Machine Learning Ethics, 8(2), 45-67. https://doi.org/10.9999/jmle.2023.4567

"""


def create_sample_pdf(output_path: str) -> str:
    """Tạo PDF từ nội dung essay."""
    try:
        from fpdf import FPDF
    except ImportError:
        subprocess.run(["pip", "install", "fpdf2"], check=True)
        from fpdf import FPDF

    class PDF(FPDF):
        def header(self):
            pass

        def footer(self):
            self.set_y(-15)
            self.set_font("helvetica", style="I", size=8)
            self.cell(0, 10, f"Page {self.page_no()}", align="C")

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("helvetica", style="B", size=16)
    pdf.multi_cell(0, 10, "Deep Learning for Natural Language Processing: A Comprehensive Survey")
    pdf.ln(5)

    # Abstract-like intro
    pdf.set_font("helvetica", style="I", size=10)
    pdf.multi_cell(0, 6, "This essay provides a survey of recent advances in deep learning for NLP, "
                          "covering transformer architectures, pre-training methods, and emerging challenges.")
    pdf.ln(8)

    # Body text
    pdf.set_font("helvetica", size=11)
    for para in ESSAY_CONTENT.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if para.startswith("#"):
            # Section header
            pdf.ln(3)
            pdf.set_font("helvetica", style="B", size=13)
            pdf.multi_cell(0, 8, para.strip("# ").strip())
            pdf.ln(2)
            pdf.set_font("helvetica", size=11)
        elif para.startswith("["):
            # Reference list header
            pdf.ln(5)
            pdf.set_font("helvetica", style="B", size=12)
            pdf.multi_cell(0, 8, para)
            pdf.ln(2)
            pdf.set_font("helvetica", size=10)
        elif para.startswith(("Vaswani", "Devlin", "He, K", "Xiao", "Brown", "Kiela", "Zhang, Q", "Zhang, X")):
            # Reference entry
            pdf.set_font("helvetica", size=10)
            pdf.multi_cell(0, 5.5, para)
            pdf.ln(1)
        else:
            # Regular paragraph
            pdf.set_font("helvetica", size=11)
            pdf.multi_cell(0, 6, para)
            pdf.ln(4)

    # Save
    pdf.output(output_path)
    return output_path


if __name__ == "__main__":
    output = "data/essays/essay_03_comprehensive.pdf"
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    create_sample_pdf(output)
    print(f"Created: {output}")

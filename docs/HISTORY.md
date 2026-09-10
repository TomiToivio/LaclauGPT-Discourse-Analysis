# LaclauGPT history and predecessor repositories

LaclauGPT is named as a tribute to [Ernesto Laclau](https://en.wikipedia.org/wiki/Ernesto_Laclau). The original pipeline was developed by Tomi Toivio in connection with the [Helsinki Hub on Emotions, Populism and Polarisation](https://www.helsinki.fi/en/researchgroups/emotions-populism-and-polarisation) and research projects funded by the European Union and the Research Council of Finland.

Earlier project contexts included:

- [CO3](https://www.co3socialcontract.eu/), research on the social contract;
- [ENDURE](https://www.endure-project.org/), research on the post-pandemic world;
- [PLEDGE](https://www.pledgeproject.eu/), research on grievance politics.

## EP2024 predecessor work

The predecessor pipeline was used to collect and analyse multimodal social-media data related to the 2024 European Parliament elections. TikTok and Instagram material was collected from 1 May 2024 until election day, 9 June 2024, using official candidate usernames, hashtags and search queries. The work covered Bulgaria, Croatia, Finland, France, Germany, Hungary, Portugal, Spain and Sweden. The collected and analysed research data is not released openly; the public repositories contain code, documentation and safe examples instead.

The work was split across two repositories:

- [LaclauGPT-TikTok-Scraper](https://github.com/TomiToivio/LaclauGPT-TikTok-Scraper) provided a Firefox extension and Node.js REST backend for research collection. It was functional for the 2024 study and is now archival. Its network-response capture architecture is carried forward under `collector/` in the current repository.
- [LaclauGPT-Multimodal-Analysis](https://github.com/TomiToivio/LaclauGPT-Multimodal-Analysis) provided Ollama-driven batch analysis on the CSC Puhti supercomputer, including OpenCV frame extraction, EasyOCR, Whisper transcripts, multimodal frame analysis, structured post-processing and Laclau/Palonen-oriented populism analysis.

The current `LaclauGPT-Discourse-Analysis` repository is a substantial redesign rather than a frozen reproduction of those systems. It keeps historical compatibility where useful while moving active development to a project/arena/machine/execution configuration model, evidence-linked theory coding, explicit human review and a reusable collection/analysis platform.

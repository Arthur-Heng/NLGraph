## Can Language Models Solve Graph Problems in Natural Language?

paper link: [https://arxiv.org/abs/2305.10037](https://arxiv.org/abs/2305.10037)

Check out the NLGraph dataset! `main.json` in each task features a supervised fine-tuning setting and is divided into `train.json` and `test.json`. The `graph` directory in each task contains the raw graph data (i.e. graph represented by numbers) divided into easy, (medium) and hard. In the raw graph data, the first two numbers in the first line are the number of nodes and edges and the following lines give the edges and queries. 

### Evaluation

**Environment:** `conda env create -f environment.yml` would generate a conda environment called `NLGraph` that should be able to run the code.

First set your openai key `OEPNAI_API_KEY` (and openai organization `OPENAI_ORGANIZATION` optionally):
```
$env:OPENAI_API_KEY="your openai key" # for Windows powershell
export OPENAI_API_KEY="your openai key" # for Linux
```
then run the evaluation code for a specific task:
```
python evaluation/<task_name>.py --model <name of LM> --mode <difficulty_mode> --prompt <prompting technique> --T <temperature> --token <max number of token> --SC <whether to use self-consistency> --SC_num <sampling number for SC>
```
For instance,
```
python evaluation/cycle.py --model text-davinci-003 --mode easy --prompt CoT --SC 1 --SC_num 5
```
evaluates `text-davinci-003` model on the easy subset of cycle task, using chain-of-thought prompting together with self-consistency.

More complete repo coming soon...
### Citation
If you find this repo useful, please cite our paper:
```
@inproceedings{
wang2023can,
title={Can Language Models Solve Graph Problems in Natural Language?},
author={Heng Wang and Shangbin Feng and Tianxing He and Zhaoxuan Tan and Xiaochuang Han and Yulia Tsvetkov},
booktitle={Thirty-seventh Conference on Neural Information Processing Systems},
year={2023},
url={https://openreview.net/forum?id=UDqHhbqYJV}
}
```

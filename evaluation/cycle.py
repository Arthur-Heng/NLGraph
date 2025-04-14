import os
import sys
import json
import argparse
import numpy as np
import networkx as nx
from tqdm import tqdm
from datetime import datetime, timedelta, timezone
from tenacity import retry, stop_after_attempt, wait_random_exponential

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.wrappers import (
    call_openai_chat,
    call_deepseek_chat,
    call_anthropic_claude,
)

# Argument Parsing
parser = argparse.ArgumentParser(description="cycle")
parser.add_argument('--model', type=str, default="gpt-3.5-turbo")
parser.add_argument('--provider', type=str, default="openai")
parser.add_argument('--mode', type=str, default="easy")
parser.add_argument('--prompt', type=str, default="none")
parser.add_argument('--T', type=int, default=0)
parser.add_argument('--token', type=int, default=400)
parser.add_argument('--SC', type=int, default=0)
parser.add_argument('--SC_num', type=int, default=5)
parser.add_argument('--dry_run', action='store_true')
args = parser.parse_args()

assert args.prompt in [
    "CoT", "none", "0-CoT", "LTM", "PROGRAM", "k-shot", "Instruct",
    "Algorithm", "Recitation", "hard-CoT", "medium-CoT"
]

total_input_tokens = 0
total_output_tokens = 0

def translate(edge, n, args):
    Q = ''
    if args.prompt in ["CoT", "k-shot", "Instruct", "Algorithm", "Recitation", "hard-CoT", "medium-CoT"]:
        with open("NLGraph/cycle/prompt/" + args.prompt + "-prompt.txt", "r") as f:
            exemplar = f.read()
        Q += exemplar + "\n\n\n"

    Q += f"In an undirected graph, (i,j) means that node i and node j are connected with an undirected edge.\n"
    Q += f"The nodes are numbered from 0 to {n-1}, and the edges are:"
    for (u, v) in edge:
        Q += f" ({u},{v})"
    Q += ".\n"

    Q += "Q: Is there a cycle in this graph?\n"
    Q += "A: Please answer at the start clearly with either 'Yes, there is a cycle.' or 'No, there is no cycle.'\n"

    if args.prompt == "Instruct":
        Q += "Let's construct a graph with the nodes and edges first and solve the graph based on that\n"

    if args.prompt == "Recitation":
        Q = Q + "Q1: Are node "+str(edge[0][0])+" and node " +str(edge[0][1])+" connected with an edge?\nA1: Yes.\n"
        u = -1
        for i in range(n):
            if u != -1:
                break
            for j in range(n):
                if [i,j] not in edge:
                    u, v = i, j
                    break
        Q = Q + "Q2: Are node "+str(u)+" and node " +str(v)+" connected with an edge?\nA2: No.\n"

    match args.prompt:
        case "0-CoT":
            Q = Q + " Let's think step by step:\n"
        case "LTM":
            Q = Q + " Let's break down this problem:\n"
        case "PROGRAM":
            Q = Q + " Let's solve the problem by a Python program and get the Final answer from there \n"

   
    return Q

@retry(wait=wait_random_exponential(min=1, max=30), stop=stop_after_attempt(3))
def predict(Q_list, args):
    global total_input_tokens, total_output_tokens
    answer_list = []
    raw_list = []

    if args.dry_run:
        print("\n========== DRY RUN: Prompt Only ==========\n")
        for i, prompt in enumerate(Q_list):
            print(f"\n--- Prompt #{i+1} ---\n{prompt}\n")
        return ["(dry run - no API call)" for _ in Q_list], ["(dry run - no raw)" for _ in Q_list]

    for prompt in Q_list:
        if args.provider == "openai":
            response, usage, raw = call_openai_chat(args.model, prompt, return_usage=True)
            total_input_tokens += usage.get("prompt_tokens", 0)
            total_output_tokens += usage.get("completion_tokens", 0)
        elif args.provider == "anthropic":
            response = call_anthropic_claude(args.model, prompt)
            raw = response
        elif args.provider == "deepseek":
            response, _, raw = call_deepseek_chat(args.model, prompt, return_usage=True)
        else:
            raise ValueError(f"Unsupported provider: {args.provider}")

        answer_list.append(response)
        raw_list.append(raw if isinstance(raw, str) else raw.choices[0].message.content)
    return answer_list, raw_list

def log(Q_list, res, answer, raw_list, args):
    utc_dt = datetime.utcnow().replace(tzinfo=timezone.utc)
    bj_dt = utc_dt.astimezone(timezone(timedelta(hours=8)))
    timestamp = bj_dt.strftime("%Y%m%d---%H-%M")
    folder = f'log/cycle/{args.model}-{args.mode}-{timestamp}-{args.prompt}'
    if args.SC:
        folder += "+SC"
    os.makedirs(folder, exist_ok=True)

    np.save(os.path.join(folder, "res.npy"), res)
    np.save(os.path.join(folder, "answer.npy"), answer)

    with open(os.path.join(folder, "prompt.txt"), "w") as f:
        for Q in Q_list:
            f.write(Q + "\n\n")
        f.write(f"Acc: {res.sum()}/{len(res)}\n")
        print(args, file=f)

    full_folder = f'log/cycle/fullresponses'
    os.makedirs(full_folder, exist_ok=True)
    with open(os.path.join(full_folder, f"{args.model}-{args.mode}-{timestamp}-{args.prompt}.txt"), "w", encoding="utf-8") as f:
        for raw in raw_list:
            f.write("=== RAW RESPONSE ===\n")
            f.write(raw + "\n\n")

def main():
    if not args.dry_run and 'OPENAI_API_KEY' not in os.environ:
        raise Exception("Missing OpenAI API Key!")

    with open("NLGraph/cycle/main.json", "r") as f:
        main_data = json.load(f)

    mode_index = {
        "easy": 0,
        "medium": 150,
        "hard": 750
    }

    g_num = {
        "easy": 10,
        "medium": 600,
        "hard": 400

        # "easy": 150,
        # "medium": 600,
        # "hard": 400
    }[args.mode]

    batch_num = 20
    res, answer, all_raw = [], [], []

    for i in tqdm(range((g_num + batch_num - 1) // batch_num)):
        Q_list = []
        for j in range(i * batch_num, min(g_num, (i + 1) * batch_num)):
            with open(f"NLgraph/cycle/graph/{args.mode}/standard/graph{j}.txt", "r") as f:
                n, m = map(int, f.readline().split())
                edges = [list(map(int, line.strip().split())) for line in f]
                Q = translate(edges, n, args)
                Q_list.append(Q)

        sc = args.SC_num if args.SC else 1
        sc_list = [[] for _ in range(sc)]
        raw_sc_list = [[] for _ in range(sc)]

        for k in range(sc):
            print(f"Running call #{k + 1}...")
            answer_list, raw_list = predict(Q_list, args)
            print(f"Finished call #{k + 1}")
            sc_list[k] = answer_list
            raw_sc_list[k] = raw_list

        for j in range(len(Q_list)):
            idx = mode_index[args.mode] + (i * batch_num + j)
            # question = main_data[str(idx)]["question"]
            # print(f"question #{question}")

            correct_answer = main_data[str(idx)]["answer"].strip().lower()
            # print(f"Correct Answer #{correct_answer}")
            expected = "yes" if "there is a cycle" in correct_answer else "no"

            vote = 0
            for k in range(sc):
                ans = sc_list[k][j].strip().lower()
                prediction = "yes" if ans.startswith("yes") else "no"
                vote += int(prediction == expected)
                answer.append(ans)
                all_raw.append(raw_sc_list[k][j])

            res.append(1 if vote * 2 >= sc else 0)

    log(Q_list, np.array(res), np.array(answer), all_raw, args)
    print("Final Accuracy:", sum(res), "/", len(res))
    print("\n=== Token Usage Summary ===")
    print(f"Total Input Tokens:  {total_input_tokens}")
    print(f"Total Output Tokens: {total_output_tokens}")
    total_cost = (total_input_tokens / 1000) * 0.005 + (total_output_tokens / 1000) * 0.015
    print(f"Estimated Cost: ${total_cost:.4f}")

if __name__ == "__main__":
    main()

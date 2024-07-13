import os
import json
from tqdm import tqdm
from groq import Groq
from openai import OpenAI
import re
openai_client = OpenAI(
    api_key=os.environ.get("AI_HUB_MIX_API_KEY"),
    base_url="https://aihubmix.com/v1"
)
groq_client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://groq.huggingtiger.asia/",
)


naive_prompt = """
你是一个BGP商业关系判断专家，请根据以下信息判断两个AS（自治域系统）之间的BGP商业关系
输入：<AS Path>， <clique>， <传输度>

<商业关系>：请你推断出<AS Path>中的AS节点对之间的商业关系，商业关系类型为c2p, p2p

你需要输出各个AS之间的商业关系，格式为：ASN1-ASN2: <商业关系>
"""

# 目前未使用
system_prompt_rule = """
你是一个BGP商业关系判断专家，请根据以下信息判断两个AS（自治域系统）之间的BGP商业关系

输入：<AS Path>， <clique>， <传输度>，<VP>
其中，<AS Path>是一个有向的AS序列（如23-32-320)，<clique>是一个AS集合（如23, 32），<传输度>是相邻链路中出现在AS两侧的唯一邻居的数量。

注释：X>Y代表X和Y是provider-customer(c2p)的关系, X-Y代表X和Y是peer-to-peer(p2p)的关系，X?Y代表X和Y的关系未知

商业关系的判断规则如下：

1.按照传输度排序，除了clique内容，若有相连的X Y Z，如果存在X>Y?Z或者X-Y?Z，则推断X>Y， 注意 此时X的传输度需要高于Z

2.X Y Z，如果X是部分VP，Z是stub，则推断Y>Z(目前这两条规则都验证不了)

3.如果存在W>X?Y,如果Y>X且存在W X Y结尾的路径，则推断W>X>Y

4.自顶向下，跳过clique成员，W X Y，如果W没有向它的provider或者peer宣告X，则推断W-X>Y

5.X Y，如果X为clique，而Y为stub，则X>Y

6.如果存在相邻的链接都未分类，X Y Z，如果不存在X<Y，则推断Y>Z

7.不满足以上规则的剩余的链接推断为p2p类型

<商业关系>：customer-provider(c2p)，peer-peer(p2p)，如果无法判断，输出unknown。

请直接输出你推断出的<商业关系>(c2p或p2p)，不要输出其他内容。
"""

zero_shot_system_prompt = f"""
You are a BGP (Border Gateway Protocol) business relationship expert. Please determine the BGP business relationships between AS(Autonomous Systems) based on the following information:

Input: <AS Path>, additional information (such as <clique>, <transit degree>, etc.)

<Business Relationship>: Please infer the business relationship between AS node pairs in the <AS Path>. The types of business relationships are p2c(provider-to-customer) and p2p(peer-to-peer).

You need to output the business relationship between each AS pair in the following format:
output_format: ASN1-ASN2: <Business Relationship>, after analyzing every AS pair in the <AS Path>, you must return the results as a list which looks like["ASN1-ASN2: ", "ASN3-ASN4: ", ...]
"""


one_shot_system_prompt = f"""
You are a BGP (Border Gateway Protocol) business relationship expert. Please determine the BGP business relationships between Autonomous Systems (AS) based on the following information and identify any potential route leakage:

Input: <AS Path>, additional information (such as <clique>, <transit degree>, etc.)

<Business Relationship>: Please infer the business relationships between AS node pairs in the <AS Path>. The types of business relationships are p2c (provider-to-customer) and p2p (peer-to-peer).

I'll give you an example to help you understand the task:
Example1: AS Path: 3356-1239-721, transit degree: 3286, 989, 6, clique member: 1239, 3356, VP: 1239, 3356
output_format: ["3356-1239": p2p,"1239-721": p2c]

You need to:

Output the business relationships between each AS pair in the following format:
output_format: ASN1-ASN2: <Business Relationship>, after analyzing every AS pair in the <AS Path>, 
you must return the results as a list in the form: ["ASN1-ASN2: ", "ASN3-ASN4: ", ...]
"""

system_prompt = f"""{zero_shot_system_prompt}"""


user_content_list = []
with open("/home/yyc/NLGraph/BGPAgent/program_data/type1_input.json", "r") as f:
    user_content_list = json.load(f)

output_list = []
for user_content in tqdm(user_content_list):
    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": user_content['question'],
        }]
    llama3_70b_chat_completion = groq_client.chat.completions.create(
        model="llama3-70b-8192",
        messages=messages,
        temperature=0.0  # Optional
    )
    # llama3_8b_chat_completion = groq_client.chat.completions.create(
    #     model= "llama3-8b-8192",
    #     messages=message,
    #     temperature=0.0  # Optional
    #     )
    # mistral_8_7b_chat_completion = groq_client.chat.completions.create(
    #     model= "mixtral-8x7b-32768",
    #     messages=message,
    #     temperature=0.0  # Optional
    #     )
    # gemma_7b_chat_completion = groq_client.chat.completions.create(
    #     model= "gemma-7b-it",
    #     messages=message,
    #     temperature=0.0  # Optional
    #     )
    openai_chat_completion = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.0,
    )
    openai_turbo_chat_completion = openai_client.chat.completions.create(
        model="gpt-4-turbo",
        messages=messages,
        temperature=0.0,
    )
    claude_chat_completion = openai_client.chat.completions.create(
        model="claude-3-5-sonnet-20240620",
        messages=messages,
        temperature=0.0,
    )
    pattern = re.compile(r'\[.*?\]', re.DOTALL)
    llama3_70b_output = llama3_70b_chat_completion.choices[0].message.content
    # llama3_8b_output=llama3_8b_chat_completion.choices[0].message.content
    # mistral_8_7b_output=mistral_8_7b_chat_completion.choices[0].message.content
    # gemma_7b_output=gemma_7b_chat_completion.choices[0].message.content
    gpt4_output = openai_chat_completion.choices[0].message.content
    gpt4_turbo_output = openai_turbo_chat_completion.choices[0].message.content
    claude3__5_output = claude_chat_completion.choices[0].message.content
    user_content["llama3-70b-answer"] = llama3_70b_output
    user_content["llama3-70b-answer-list"] = pattern.findall(llama3_70b_output)
    # user_content["mistral-8-7b-answer"] = mistral_8_7b_output
    # user_content["llama3-8b-answer"] = llama3_8b_output
    # user_content["gemma-7b-answer"] = gemma_7b_output
    user_content["gpt-4o-answer"] = gpt4_output
    user_content["gpt-4o-answer-list"] = pattern.findall(gpt4_output)
    user_content["gpt-4-turbo-answer"] = gpt4_turbo_output
    user_content["gpt-4-turbo-answer-list"] = pattern.findall(
        gpt4_turbo_output)
    user_content["claude-3-5-sonnet-20240620-answer"] = claude3__5_output
    user_content["claude-3-5-sonnet-20240620-answer-list"] = pattern.findall(
        claude3__5_output)
    # print(user_content)
    output_list.append(user_content)
    with open("/home/yyc/NLGraph/BGPAgent/program_data/cache/cache.json", "w", encoding='utf-8') as f:
        json.dump(output_list, f, ensure_ascii=False, indent=4)

with open("/home/yyc/NLGraph/BGPAgent/program_data/type1_english_output_0713_zero_shot_temperation=0.json", "w", encoding='utf-8') as f:
    json.dump(output_list, f, ensure_ascii=False, indent=4)

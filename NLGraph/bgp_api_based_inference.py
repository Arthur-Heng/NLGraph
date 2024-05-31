import os
import json
from tqdm import tqdm
from groq import Groq
from openai import OpenAI
openai_client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)


system_prompt = """
你是一个BGP商业关系判断专家。请根据以下信息判断两个AS之间的BGP商业关系，商业关系的判断规则如下：
输入： AS Path， Clique， 传输度和VP信息

规则：

1.按照传输度排序，除了clique内容，若有相连的X Y Z，如果存在X>Y?Z或者X-Y?Z，则推断X>Y， 注意 此时X的传输度需要高于Z

2.X Y Z，如果X是部分VP，Z是stub，则推断Y>Z

3.如果存在W>X?Y,如果Y>X且存在W X Y结尾的路径，则推断W>X>Y

4.自顶向下，跳过clique成员，W X Y，如果W没有向它的provider或者peer宣告X，则推断W-X>Y

5.X Y，如果X为clique，而Y为stub，则X>Y

6.如果存在相邻的链接都未分类，X Y Z，如果不存在X<Y，则推断Y>Z

不满足以上规则的剩余的链接推断为p2p类型

<商业关系>：customer-provider，peer-peer，sibling-sibling，或者p2p。如果无法判断，输出unknown。

请直接输出你推断出的<商业关系>，不要输出其他内容。
"""
user_content_list = []
with open("/Users/alex/Projects/NLGraph/NLGraph/BGP/type1_output.json", "r") as f:
    user_content_list = json.load(f)

output_list = []
for user_content in tqdm(user_content_list):
    llama3_chat_completion = client.chat.completions.create(
        model= "llama3-8b-8192",
        messages=[
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": user_content['question'],
        }],)
    openai_chat_completion = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": user_content['question'],
        }
    ],)
    llama3_output=llama3_chat_completion.choices[0].message.content
    gpt4_output=openai_chat_completion.choices[0].message.content
    user_content["llama3-8b-answer"] = llama3_output
    user_content["gpt-4o-answer"] = gpt4_output
    # output_item = {
    #     "question": user_content['question'], 
    #     "llam3-70b-answer": llama3_output, 
    #     "gpt-4-turbo-answer": gpt4_output
    # }
    print(user_content)
    output_list.append(user_content)

with open("/Users/alex/Projects/NLGraph/NLGraph/BGP/type1_output_plus.json", "w", encoding='utf-8') as f:
    json.dump(output_list, f, ensure_ascii=False, indent=4)

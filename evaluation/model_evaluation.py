import json

from tqdm import tqdm
from transformers import AutoTokenizer
import torch

import sys

sys.path.append("../")
from component.utils import ModelUtils


def main():
    # 使用base model和adapter进行推理，无需手动合并权重
    model_name_or_path = '/root/autodl-tmp/jiangxia/base_model/Qwen-14B-Chat'
    #    adapter_name_or_path = '/root/autodl-tmp/jiangxia/finetune/qwen_qlora/trained_models/Qwen-14B-Chat-Keywords-1118-match-1124/final'
    adapter_name_or_path = '/root/autodl-tmp/qwen_qlora/trained_models/Qwen-14B-Chat-Keywords-1118-match-1124/final'

    # 直接使用 合并 model
    # model_name_or_path = '/root/autodl-tmp/qwen_qlora/trained_models/Qwen-14B-nlp-merge'
    # adapter_name_or_path = None

    # 是否使用4bit进行推理，能够节省很多显存，但效果可能会有一定的下降
    load_in_4bit = False

    # 生成超参配置
    max_new_tokens = 500
    top_p = 0.9
    temperature = 0.35
    repetition_penalty = 1.0
    device = 'cuda'

    # 加载模型
    model = ModelUtils.load_model(
        model_name_or_path,
        load_in_4bit=load_in_4bit,
        adapter_name_or_path=adapter_name_or_path
    ).eval()

    print("加载模型")

    tokenizer = AutoTokenizer.from_pretrained(
        model_name_or_path,
        trust_remote_code=True,
        # llama不支持fast
        use_fast=False if model.config.model_type == 'llama' else True
    )

    print("加载 tokenizer")

    # QWenTokenizer比较特殊，pad_token_id、bos_token_id、eos_token_id均为None。eod_id对应的token为<|endoftext|>
    if tokenizer.__class__.__name__ == 'QWenTokenizer':
        tokenizer.pad_token_id = tokenizer.eod_id
        tokenizer.bos_token_id = tokenizer.eod_id
        tokenizer.eos_token_id = tokenizer.eod_id

    tokenizer.padding_side = "left"

    print('设置 tokenizer.padding_side = "left"')

    with open('/root/autodl-tmp/qwen_qlora/data/text_matching_data_test.jsonl',
              'r', encoding='utf-8') as read_file, \
            open('/root/autodl-tmp/qwen_qlora/data/text_matching_data_test_result.csv',
                 'w+', encoding='utf-8') as write_file:
        lines = read_file.readlines()
        print("开始加载文件")
        correct_number = 0
        total = 0
        for line in tqdm(lines, ncols=10):
            total += 1
            line = line.strip()
            line_json = json.loads(line)
            text = line_json['conversation'][0]['human']
            result = line_json['conversation'][0]['assistant']

            input_ids = tokenizer(text, return_tensors="pt", add_special_tokens=False).input_ids.to(device)
            bos_token_id = torch.tensor([[tokenizer.bos_token_id]], dtype=torch.long).to(device)
            eos_token_id = torch.tensor([[tokenizer.eos_token_id]], dtype=torch.long).to(device)
            input_ids = torch.concat([bos_token_id, input_ids, eos_token_id], dim=1)

            with torch.no_grad():
                outputs = model.generate(
                    input_ids=input_ids, max_new_tokens=max_new_tokens, do_sample=True,
                    top_p=top_p, temperature=temperature, repetition_penalty=repetition_penalty,
                    eos_token_id=tokenizer.eos_token_id, pad_token_id=151643
                )

            outputs = outputs.tolist()[0][len(input_ids[0]):]
            response = tokenizer.decode(outputs)
            response = response.strip().replace(tokenizer.eos_token, "").strip()
            if response == result:
                correct_number += 1
            write_file.write(text.replace('\n', '。') + '\t 原始结果：' + result + '\t 模型结果:' + response + '\n')

    print(f"correct number {correct_number}, total #{total}, ratio is {correct_number / total}")


if __name__ == '__main__':
    main()

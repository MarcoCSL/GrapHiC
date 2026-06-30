import json
import torch
from openai_harmony import (
	Conversation,
	Message,
	Role,
	SystemContent,
	DeveloperContent,
	ReasoningEffort
)


def llm_answer(model, llm_name, tokenizer, template, question, reasoning_effort=ReasoningEffort.MEDIUM):

	if supports_reasoning(llm_name):
		system = (
			SystemContent.new()
			.with_required_channels(["final"])
			.with_reasoning_effort(reasoning_effort)
		)

		developer_message = (DeveloperContent.new().with_instructions(template))

		convo = Conversation.from_messages([
			Message.from_role_and_content(Role.SYSTEM, system),
			Message.from_role_and_content(Role.DEVELOPER, developer_message),
			Message.from_role_and_content(Role.USER, question)
		])

		prefill_ids = tokenizer.render_conversation_for_completion(conversation=convo, next_turn_role=Role.ASSISTANT, config=None)
		stop_token_ids = tokenizer.stop_tokens_for_assistant_actions()

		input_ids_tensor = torch.tensor([prefill_ids], dtype=torch.long, device="cuda")

		outputs = model.generate(
			input_ids=input_ids_tensor,
			max_new_tokens=1024,
			eos_token_id=stop_token_ids
		)

		completion_ids = outputs[0][len(prefill_ids):]
		
		try:
			entries = tokenizer.parse_messages_from_completion_tokens(completion_ids, Role.ASSISTANT)
			response = ""
			for message in entries:
				msg_dict = message.to_dict()
				if "final" in msg_dict['channel']:
					response = msg_dict['content'][0]['text']
					break
			
			ans = response
		except RuntimeError:
			raw_text = tokenizer.decode(completion_ids)
			ans = extract_final_message(raw_text)
		
		torch.cuda.empty_cache()

	else:
		if tokenizer.pad_token is None:
			tokenizer.pad_token = tokenizer.eos_token

		model.config.pad_token_id = tokenizer.pad_token_id
		model.generation_config.pad_token_id = tokenizer.pad_token_id

		messages = [
			{"role": "system", "content": template},
			{"role": "user", "content": question}
		]

		text = tokenizer.apply_chat_template(
			messages,
			tokenize=False,
			add_generation_prompt=True,
			enable_thinking=False
		)

		inputs = tokenizer(
			text,
			return_tensors="pt",
			padding=True
		).to(model.device)

		outputs = model.generate(
			**inputs,
			max_new_tokens=512,
			pad_token_id=tokenizer.pad_token_id,
			eos_token_id=tokenizer.eos_token_id
		)

		input_len = inputs["input_ids"].shape[1]
		generated_tokens = outputs[0][input_len:]

		ans = tokenizer.decode(
			generated_tokens,
			skip_special_tokens=True
		).strip()

	return ans

def extract_final_message(text):
    start_token = "<|channel|>final<|message|>"
    end_token = "<|return|>"
    
    start = text.find(start_token)
    if start == -1:
        return text
    
    start += len(start_token)
    end = text.find(end_token, start)
    if end == -1:
        return text
    
    return text[start:end].strip()

def ans_to_dict(ans):
	try:
		ans = json.loads(ans)
	except Exception:
		ans = {}
	return ans

def supports_reasoning(llm_name):
	return "gpt-oss" in llm_name.lower()
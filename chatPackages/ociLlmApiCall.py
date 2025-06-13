import oci
import json

CONFIG_PROFILE = "DEFAULT"
config = oci.config.from_file('configuration/oci_ai_config.txt', CONFIG_PROFILE)


def get_llm_response(
        input_prompt,
        compartment_id="ocid1.compartment.oc1..aaaaaaaa4s2upstujcl2qp2kz5zw2v2a7cc3naotw3cgybjsp2neoxumqncq",
        endpoint="https://inference.generativeai.uk-london-1.oci.oraclecloud.com",
        model_id="ocid1.generativeaimodel.oc1.uk-london-1.amaaaaaask7dceyawkuqmlvc264uxta37644rttlezku42uxwnzhn54tc27a"
):
    generative_ai_inference_client = oci.generative_ai_inference.GenerativeAiInferenceClient(
        config=config,
        service_endpoint=endpoint,
        retry_strategy=oci.retry.NoneRetryStrategy(),
        timeout=(10, 240)
    )
    chat_detail = oci.generative_ai_inference.models.ChatDetails()

    content = oci.generative_ai_inference.models.TextContent()
    content.text = input_prompt
    message = oci.generative_ai_inference.models.Message()
    message.role = "USER"
    message.content = [content]
    chat_request = oci.generative_ai_inference.models.GenericChatRequest()
    chat_request.api_format = oci.generative_ai_inference.models.BaseChatRequest.API_FORMAT_GENERIC
    chat_request.messages = [message]
    chat_request.max_tokens = 4000
    chat_request.temperature = 0.75
    chat_request.frequency_penalty = 0
    chat_request.presence_penalty = 0
    chat_request.top_p = 0.75
    chat_request.top_k = -1

    chat_detail.serving_mode = oci.generative_ai_inference.models.OnDemandServingMode(model_id=model_id)
    chat_detail.chat_request = chat_request
    chat_detail.compartment_id = compartment_id
    chat_response = generative_ai_inference_client.chat(chat_detail)
    # Print result
    # print(vars(chat_response))
    res_text = {}
    if hasattr(chat_response.data, "chat_response"):
        res = chat_response.data.chat_response
        res = json.loads(str(res))
        # print(res)
        res_text = res['choices'][0]['message']['content'][0]['text']
        # print(res_text)

    return res_text


if __name__ == '__main__':
    l_input = f'''
Your agenda is to create a FAQ questions for the information provided related to WInfoBots Solution. 
This FAQ questions will be helpful for Sales team to answer them to the clients, so create questions assuming that you heard about the topic which will be provided as an input and then answer the question based on the input provided assumingg you are an WInfoBots expert. 
Make the questions as depth as possible and elaborate answers as much as possible so my sales team have the best information to gear up for the sales discussion. 
Generate the maximum possible questions we may get based content provided.
For each question, provide a detailed and elaborate answer, in the json structure as provided below:
{{ "result":[
{{
  "question": "<question>",
  "answer": "<answer based on the content>"
}},
{{
  "question": "<question>",
  "answer": "<answer based on the content>"
}}
]
}}

Given the following text:
["Imagine this your team is buried under a mountain of repetitive tasks. Data entry, report generation - you name it, they're doing it. It's like they're stuck at the bottom of a pyramid, spending all their time on the mundane stuff.
Wouldn't it be great if you could flip that pyramid upside down? Is your team at the top, focusing on strategy, analysis, and making a real impact? That's where automation comes in.
This is the reality for many shared services teams. They're juggling countless tasks across finance, accounting, HR, and procurement, leaving little time for analysis, reporting, or strategic thinking.
In today’s fast-paced business environment, automation isn’t just an option; it’s imperative. We recognized this challenge early on. It was clear that the traditional pyramid structure—where most of the effort is spent on transaction processing—needed to be inverted. Our goal was to reduce the time spent on these mundane tasks and give that time back to the business, allowing teams to concentrate on higher-value work.
That's when we started exploring automation. We started by closely examining the various functions within finance, accounting, procurement, and HR. We identified repetitive, manual, and rule-based processes—ideal candidates for automation. 
These processes could be automated to streamline operations regardless of where the team was located, whether within the business or in a shared services center.
Through years of experience with Oracle applications, we developed a deep understanding of these challenges. We knew that while Oracle is a powerful tool, it's the processes and human interactions around it that often create bottlenecks.
This journey led us to create WinfoBots. Our goal was to build a solution that could automate these repetitive tasks, improve efficiency, and allow teams to focus on higher-value work."]
    '''
    print(f"final res: {get_llm_response(l_input)}")

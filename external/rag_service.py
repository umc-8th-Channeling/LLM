from external.youtube_service import youtubeService  # 유튜브 자막 처리 서비스
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.prompts.chat import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain


class RagService:
    def summarize_video(video_id: str) -> str:
        context = youtubeService.get_formatted_transcript(video_id) #// 유튜브 자막 가져오기
        print("정리된 자막 = ", context)
        print()
        documents = [Document(page_content=context)]# // 다큐멘트화 하기

        llm = ChatOpenAI(model="gpt-4o-mini") #// llm 모델 설정

        # 5. 프롬프트 설정
        prompt_template = PromptTemplate(
            input_variables=["input", "context"],
            template="""
    당신은 유튜브 영상 자막을 분석해 구간별 개요를 작성하는 AI입니다.
자막은 실제 영상의 전체 내용을 포함하고 있으며, 당신의 목표는 이 자막을 기반으로 10초 단위로 영상의 흐름을 정리하는 것입니다.
- 각 소제목은 영상의 주제를 대표해야 합니다.
- 각 구간은 영상 흐름을 반영하여 약 10초 단위(±5초 허용)로 구분해야 합니다.
- 출력은 반드시 위의 예시 형식을 따르며, 불필요한 부가 설명 없이 개요만 출력해야 합니다.
- 각 구간의 제목과 시간 범위를 표시하세요.
- 각 구간 설명은 3인칭 시점으로, 객관적으로 간결하게 서술하세요.
- 1인칭 표현(예: "나는", "내가") 대신 "화자", "그/그녀", "인터뷰어" 등의 표현을 사용하세요.
- 각 구간별 핵심 내용은 최대 3문장 이내로 요약하세요.
- 전체 개요를 I, II, III 등으로 번호 매겨 구성하세요.
- 불필요한 로그나 시스템 메시지를 출력하지 마세요

다음과 같은 형식으로 결과를 반드시 출력해야 합니다:

다음은 제공된 영상 스크립트를 기반으로 한 유튜브 영상 개요의 번역입니다:
요구 사항:


I. 도입 (0:00 - 0:25)
화자가 자신을 대학생이라고 소개한다.  
본인의 채널 및 콘텐츠에 대해 간단히 설명한다.

II. 글쓰기와 재능 (0:25 - 0:59)  
화자는 글쓰기를 좋아한다고 말한다.  
인터뷰어는 화자에게 리더십 같은 다른 재능도 있다고 언급한다.  
화자는 자신의 리더십 능력을 과소평가한다.

...

질문: {input}
문서 내용: {context}
답변:""".strip() 
        )

        chat_prompt = ChatPromptTemplate.from_messages([
            HumanMessagePromptTemplate(prompt=prompt_template)
        ])

        # 6. 체인 조합
        combine_chain = create_stuff_documents_chain(llm, chat_prompt)

        # 7. 실행
        query = "유튜브 영상 자막을 기반으로 10초 단위 개요를 위의 형식에 따라 작성해주세요."
        result = combine_chain.invoke({"input": query, "context": documents})
        return result
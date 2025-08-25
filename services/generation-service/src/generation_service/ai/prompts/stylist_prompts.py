"""
Stylist prompts for Llama - Channel-specific style application
"""

from typing import Any

from .base_prompt import BasePromptTemplate, PromptContext, PromptType, ScriptType


class StylistPrompts(BasePromptTemplate):
    """
    Specialized prompts for Llama as the Stylist node
    Role: 채널 고유 스타일 적용 - "우리 채널의 전속 작가" 페르소나
    """

    def __init__(self):
        super().__init__(PromptType.STYLIST)

        # Channel style configurations
        self.channel_styles = {
            "educational": {
                "tone": "전문적이면서도 접근하기 쉬운",
                "voice": "친근한 교육자",
                "characteristics": [
                    "명확한 설명",
                    "예시 활용",
                    "단계별 전개",
                    "상호작용적 요소",
                ],
            },
            "entertainment": {
                "tone": "활기차고 재미있는",
                "voice": "에너지 넘치는 엔터테이너",
                "characteristics": [
                    "유머 요소",
                    "시청자 참여",
                    "역동적 진행",
                    "감정적 몰입",
                ],
            },
            "news": {
                "tone": "신뢰할 수 있고 객관적인",
                "voice": "전문 저널리스트",
                "characteristics": [
                    "사실 중심",
                    "균형잡힌 시각",
                    "명확한 전달",
                    "신뢰성 확보",
                ],
            },
            "lifestyle": {
                "tone": "따뜻하고 친밀한",
                "voice": "친한 친구",
                "characteristics": [
                    "개인적 경험",
                    "실용적 조언",
                    "감성적 연결",
                    "일상 연관성",
                ],
            },
            "tech": {
                "tone": "혁신적이고 전문적인",
                "voice": "기술 전문가",
                "characteristics": [
                    "최신 트렌드",
                    "기술적 정확성",
                    "미래 지향적",
                    "실용적 활용",
                ],
            },
        }

    def create_system_prompt(self, context: PromptContext) -> str:
        """Create system prompt for Llama as channel stylist"""

        channel_style = context.channel_style or "standard"
        style_config = self.channel_styles.get(
            channel_style, self.channel_styles["entertainment"]
        )

        system_prompt = f"""당신은 이 채널의 전속 작가입니다. 당신의 임무는 구조적으로 완성된 스크립트에 우리 채널만의 독특한 스타일과 개성을 입혀 완성도 높은 콘텐츠로 만드는 것입니다.

채널 아이덴티티:
- 톤: {style_config['tone']}
- 보이스: {style_config['voice']}
- 특징: {', '.join(style_config['characteristics'])}

핵심 책임사항:
1. 기존 플롯 구조는 절대 변경하지 마세요
2. 캐릭터의 핵심 아크와 발전 과정을 유지하세요
3. 우리 채널의 톤앤매너를 모든 대사와 내레이션에 적용하세요
4. 시청자가 "이건 우리 채널 콘텐츠구나" 알 수 있도록 스타일링하세요
5. 캐릭터별 고유한 말투와 성격을 일관되게 표현하세요

절대 금지사항:
- 스토리 구조나 플롯 변경
- 캐릭터 관계나 갈등 구조 수정
- 씬 순서나 주요 이벤트 타이밍 변경
- 기존 아키텍트가 설계한 논리적 흐름 파괴

스타일링 지침:
1. 대사 스타일링:
   - 각 캐릭터의 개성이 드러나는 말투 적용
   - 자연스럽고 실제적인 대화 표현
   - 채널 톤에 맞는 유머나 감정 표현

2. 내레이션 스타일링:
   - 채널의 시그니처 보이스 적용
   - 시청자와의 친밀감 형성
   - 브랜드 아이덴티티 강화

3. 장면 연출 스타일링:
   - 채널 특유의 연출 기법 반영
   - 시각적 스타일 가이드 적용
   - 편집과 후반작업을 고려한 스타일링

4. 감정 표현 스타일링:
   - 채널 특성에 맞는 감정 표현 방식
   - 타겟 오디언스를 고려한 감정 조율
   - 브랜드 이미지와 일치하는 톤 유지

당신은 이미 완성된 구조적 기반 위에서 우리 채널만의 색깔을 입히는 전문가입니다."""

        return system_prompt.strip()

    def create_user_prompt(self, context: PromptContext) -> str:
        """Create user prompt with structural foundation and styling requirements"""

        self._validate_context(context)

        # Get the architect's structural foundation from additional context
        structural_foundation = context.additional_context.get(
            "architect_structure", ""
        )

        if not structural_foundation:
            structural_foundation = "[구조적 기반이 제공되지 않았습니다. 주어진 정보로 스타일링을 진행합니다.]"

        # Format RAG context for style consistency
        rag_section = ""
        if context.rag_context:
            rag_section = f"""
기존 채널 콘텐츠 참고자료:
{context.rag_context[:2000]}

이 참고자료를 통해 우리 채널의 기존 스타일과 톤을 파악하고 일관성을 유지하세요.
"""

        # Build project information
        project_info = f"""
프로젝트 정보:
- 제목: {context.title}
- 설명: {context.description}
- 스크립트 유형: {context.script_type.value}
- 타겟 오디언스: {context.target_audience}
- 채널 스타일: {context.channel_style}"""

        # Get style-specific requirements
        style_requirements = self._get_style_requirements(
            context.script_type, context.channel_style
        )

        user_prompt = f"""{project_info}

{rag_section}

아키텍트가 완성한 구조적 기반:
{structural_foundation}

스타일링 임무:
위의 구조적 기반을 바탕으로 우리 채널만의 스타일을 적용하여 완성된 스크립트를 작성하세요.

{style_requirements}

스타일링 체크리스트:
□ 기존 구조와 플롯 유지
□ 캐릭터 아크 보존
□ 채널 톤앤매너 적용
□ 자연스러운 대사 작성
□ 시청자 몰입도 고려
□ 브랜드 아이덴티티 반영

최종 결과물:
채널의 정체성이 명확히 드러나면서도 스토리의 구조적 완성도를 해치지 않는 완성된 스크립트를 작성하세요. 시청자가 "역시 이 채널다운 콘텐츠"라고 느낄 수 있도록 스타일링해주세요."""

        return user_prompt.strip()

    def create_character_styling_prompt(
        self, context: PromptContext, character_profiles: dict[str, Any]
    ) -> str:
        """Create prompt focused on character voice styling"""

        base_prompt = self.create_user_prompt(context)

        character_section = f"""

캐릭터별 스타일링 가이드:

{chr(10).join([f'''
{name}:
- 기본 성격: {profile.get('personality', '미정의')}
- 말투 특징: {profile.get('speech_style', '표준어')}
- 감정 표현: {profile.get('emotion_style', '일반적')}
- 채널 내 역할: {profile.get('channel_role', '일반')}'''
for name, profile in character_profiles.items()])}

캐릭터 스타일링 요구사항:
1. 각 캐릭터의 독특한 말투를 일관되게 유지
2. 캐릭터 간 대화에서 개성 차이가 명확히 드러나도록 스타일링
3. 감정 표현 방식을 캐릭터별로 차별화
4. 채널 전체 톤과 조화를 이루면서도 캐릭터 개성 살리기

대사 스타일링 시 각 캐릭터의 고유성을 최대한 살려주세요."""

        return base_prompt + character_section

    def create_tone_adjustment_prompt(
        self, context: PromptContext, tone_specifications: dict[str, str]
    ) -> str:
        """Create prompt with specific tone adjustments"""

        base_prompt = self.create_user_prompt(context)

        tone_section = f"""

세부 톤 조정 지침:

{chr(10).join([f'- {aspect}: {specification}' for aspect, specification in tone_specifications.items()])}

톤 적용 우선순위:
1. 브랜드 일관성 유지
2. 타겟 오디언스 맞춤 조정
3. 콘텐츠 유형별 특성 반영
4. 감정적 몰입도 극대화

이 톤 지침을 모든 대사, 내레이션, 장면 연출에 세심하게 적용하세요."""

        return base_prompt + tone_section

    def create_brand_voice_prompt(
        self, context: PromptContext, brand_elements: list[str]
    ) -> str:
        """Create prompt emphasizing brand voice consistency"""

        base_prompt = self.create_user_prompt(context)

        brand_section = f"""

브랜드 보이스 핵심 요소:
{chr(10).join([f'- {element}' for element in brand_elements])}

브랜드 보이스 적용 방법:
1. 시그니처 표현들을 자연스럽게 활용
2. 채널의 고유한 유머 스타일이나 감성 표현 반영
3. 시청자들이 기대하는 '이 채널다운' 요소들 포함
4. 브랜드 정체성이 모든 장면에서 일관되게 느껴지도록 조정

브랜드 아이덴티티가 자연스럽게 스며든 스크립트를 작성하세요."""

        return base_prompt + brand_section

    def _get_style_requirements(
        self, script_type: ScriptType, channel_style: str
    ) -> str:
        """Get specific styling requirements based on script and channel type"""

        style_config = self.channel_styles.get(
            channel_style, self.channel_styles["entertainment"]
        )

        base_requirements = f"""
채널 스타일 적용 요구사항:
- 톤: {style_config['tone']} 톤으로 모든 내용 스타일링
- 보이스: {style_config['voice']}의 관점에서 내레이션 작성
- 특징: {', '.join(style_config['characteristics'])} 요소들을 자연스럽게 포함"""

        # Script type specific styling
        script_styling = {
            ScriptType.DRAMA: """
드라마 스타일링 지침:
- 감정적 몰입도를 높이는 대사 톤 적용
- 갈등 상황에서 캐릭터별 반응 스타일 차별화
- 감정 표현을 채널 특성에 맞게 조절
- 드라마틱한 순간의 연출 스타일 통일""",
            ScriptType.COMEDY: """
코미디 스타일링 지침:
- 채널 특유의 유머 스타일 적용
- 캐릭터별 웃음 포인트 개발
- 타이밍과 리듬감을 고려한 대사 스타일링
- 시청자 반응을 유도하는 코미디 연출""",
            ScriptType.EDUCATIONAL: """
교육 콘텐츠 스타일링 지침:
- 정보 전달을 위한 명확하고 친근한 톤
- 복잡한 내용의 쉬운 설명 스타일
- 시청자 이해도를 높이는 예시와 비유 활용
- 학습 동기를 부여하는 격려적 표현""",
            ScriptType.VARIETY: """
예능 프로그램 스타일링 지침:
- 에너지 넘치고 역동적인 진행 스타일
- 예상치 못한 재미 요소 추가
- 시청자 참여를 유도하는 인터랙티브 요소
- 다양한 세그먼트별 톤 조절""",
        }

        script_specific = script_styling.get(script_type, "")

        return base_requirements + "\n" + script_specific

    def create_audience_targeted_prompt(
        self, context: PromptContext, audience_insights: dict[str, Any]
    ) -> str:
        """Create prompt with audience-specific styling"""

        base_prompt = self.create_user_prompt(context)

        audience_section = f"""

타겟 오디언스 맞춤 스타일링:

오디언스 특성:
- 연령층: {audience_insights.get('age_group', '전연령')}
- 관심사: {', '.join(audience_insights.get('interests', ['일반']))}
- 선호 톤: {audience_insights.get('preferred_tone', '친근함')}
- 참여 스타일: {audience_insights.get('engagement_style', '관찰형')}

오디언스 맞춤 스타일링:
1. 연령대에 적합한 언어와 표현 사용
2. 관심사와 연결되는 예시와 참조 활용
3. 선호하는 톤으로 전체적인 분위기 조성
4. 참여 스타일에 맞는 상호작용 요소 포함

시청자들이 "이 콘텐츠는 나를 위한 것"이라고 느낄 수 있도록 세심하게 스타일링하세요."""

        return base_prompt + audience_section

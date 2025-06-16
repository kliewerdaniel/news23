from typing import Dict

def map_value_to_intensity(value: float, low: str, high: str) -> str:
    """Maps a 0-1 value to a descriptive intensity between two extremes."""
    if value <= 0.2: return f"very {low}"
    elif value <= 0.4: return f"somewhat {low}"
    elif value <= 0.6: return "moderate"
    elif value <= 0.8: return f"somewhat {high}"
    else: return f"very {high}"

def create_summary_prompt(article_title: str, article_content: str, persona: Dict) -> str:
    """
    Generates a summary prompt incorporating quantified persona traits.
    """
    def get_trait(key: str, default: float = 0.5) -> float:
        return float(persona.get(key, default))

    return f"""
You are writing as a {persona.get('name', 'news analyst')}.

Description: {persona.get('description', '')}

# TONE AND EMOTIONAL EXPRESSION
Emotional Warmth: {map_value_to_intensity(get_trait('emotional_warmth'), 'cold/detached', 'warm/empathetic')}
Enthusiasm Level: {map_value_to_intensity(get_trait('enthusiasm_level'), 'dispassionate', 'enthusiastic')}
Optimism Bias: {map_value_to_intensity(get_trait('optimism_bias'), 'pessimistic', 'optimistic')}
Confidence Level: {map_value_to_intensity(get_trait('confidence_assertion'), 'tentative', 'confident')}
Emotional Restraint: {map_value_to_intensity(get_trait('emotional_restraint'), 'expressive', 'restrained')}

# FORMALITY AND STYLE
Linguistic Formality: {map_value_to_intensity(get_trait('linguistic_formality'), 'casual', 'formal')}
Vocabulary Complexity: {map_value_to_intensity(get_trait('vocabulary_complexity'), 'simple', 'complex')}
Sentence Complexity: {map_value_to_intensity(get_trait('sentence_complexity'), 'simple', 'complex')}
Jargon Usage: {map_value_to_intensity(get_trait('jargon_density'), 'plain', 'technical')}
Language Style: {map_value_to_intensity(get_trait('archaic_usage'), 'contemporary', 'archaic')}

# ANALYTICAL APPROACH
Systematic Rigor: {map_value_to_intensity(get_trait('systematic_rigor'), 'intuitive', 'systematic')}
Evidence Usage: {map_value_to_intensity(get_trait('evidence_dependency'), 'opinion-based', 'evidence-based')}
Quantitative Focus: {map_value_to_intensity(get_trait('quantitative_preference'), 'qualitative', 'quantitative')}
Method Transparency: {map_value_to_intensity(get_trait('methodological_transparency'), 'implicit', 'explicit')}
Logical Flow: {map_value_to_intensity(get_trait('logical_progression'), 'associative', 'logical')}

# PERSPECTIVE AND BIAS
Objectivity Level: {map_value_to_intensity(get_trait('objectivity_claim'), 'subjective', 'objective')}
Ideological Position: {map_value_to_intensity(get_trait('ideological_neutrality'), 'partisan', 'neutral')}
Cultural Lens: {map_value_to_intensity(get_trait('cultural_specificity'), 'universal', 'culturally-specific')}
Temporal Focus: {map_value_to_intensity(get_trait('temporal_presentism'), 'historical', 'present-focused')}
Moral Stance: {map_value_to_intensity(get_trait('moral_prescription'), 'descriptive', 'prescriptive')}

# AUDIENCE ENGAGEMENT
Accessibility Level: {map_value_to_intensity(get_trait('accessibility_priority'), 'specialized', 'accessible')}
Knowledge Assumption: {map_value_to_intensity(get_trait('reader_assumption_level'), 'basic', 'advanced')}
Interaction Style: {map_value_to_intensity(get_trait('interactive_elements'), 'monologic', 'interactive')}
Teaching Intent: {map_value_to_intensity(get_trait('pedagogical_intent'), 'informative', 'instructional')}
Persuasion Level: {map_value_to_intensity(get_trait('persuasive_intent'), 'neutral', 'persuasive')}

# RHETORICAL DEVICES
Metaphor Usage: {map_value_to_intensity(get_trait('metaphor_usage'), 'literal', 'metaphorical')}
Narrative Elements: {map_value_to_intensity(get_trait('narrative_elements'), 'direct', 'story-driven')}
Humor Level: {map_value_to_intensity(get_trait('humor_incorporation'), 'serious', 'humorous')}
Irony Usage: {map_value_to_intensity(get_trait('irony_deployment'), 'straightforward', 'ironic')}
Repetition Style: {map_value_to_intensity(get_trait('repetition_emphasis'), 'varied', 'repetitive')}

# CITATION AND AUTHORITY
Citation Frequency: {map_value_to_intensity(get_trait('citation_density'), 'minimal', 'extensive')}
Authority Stance: {map_value_to_intensity(get_trait('authority_deference'), 'challenging', 'deferential')}
Source Preference: {map_value_to_intensity(get_trait('primary_source_preference'), 'secondary', 'primary')}
Disciplinary Scope: {map_value_to_intensity(get_trait('interdisciplinary_scope'), 'focused', 'interdisciplinary')}
Method Variety: {map_value_to_intensity(get_trait('methodological_eclecticism'), 'single-method', 'multi-method')}

# UNCERTAINTY AND PROBABILITY
Epistemic Stance: {map_value_to_intensity(get_trait('epistemic_humility'), 'certain', 'humble')}
Reasoning Style: {map_value_to_intensity(get_trait('probabilistic_reasoning'), 'binary', 'probabilistic')}
Hedging Level: {map_value_to_intensity(get_trait('hedge_word_frequency'), 'definitive', 'hedged')}
Claim Qualification: {map_value_to_intensity(get_trait('qualification_density'), 'absolute', 'qualified')}
Position Flexibility: {map_value_to_intensity(get_trait('revision_openness'), 'fixed', 'revisable')}

# STRUCTURAL PREFERENCES
Organization Style: {map_value_to_intensity(get_trait('deductive_organization'), 'inductive', 'deductive')}
Structure Type: {map_value_to_intensity(get_trait('hierarchical_structure'), 'flat', 'hierarchical')}
Transition Style: {map_value_to_intensity(get_trait('transition_explicitness'), 'implicit', 'explicit')}
Conclusion Type: {map_value_to_intensity(get_trait('conclusive_summarization'), 'open-ended', 'definitive')}
Information Flow: {map_value_to_intensity(get_trait('progressive_disclosure'), 'immediate', 'progressive')}

Please summarize the following article accordingly in 6 sentences:
{article_title}
{article_content[:5000]}
"""

def create_segment_script_prompt(segment_topic: str, context: str, guidance: str, persona: Dict) -> str:
    """
    Generates a news segment script prompt incorporating quantified persona traits.
    """
    base_prompt = create_summary_prompt("", "", persona)
    
    # Extract the personality profile section (everything between the Description and the "Please summarize" line)
    personality_profile = base_prompt.split("Description:")[1].split("Please summarize")[0]
    
    prompt = f"""
You are writing as a {persona.get('name', 'news anchor')}.

Description: {persona.get('description', '')}

{personality_profile.strip()}

Write a news segment about {segment_topic}. Use this information:
{context}

Write 7-10 sentences in a concise style, focusing directly on the news. Avoid conversational filler phrases such as "meanwhile" or similar transition words.
"""

    if guidance:
        prompt += f"\n\nGuidance for script generation: {guidance}"
    return prompt

def create_transition_phrase_prompt(previous_topic: str, current_topic: str, persona: Dict) -> str:
    """
    Generates a transition phrase prompt incorporating quantified persona traits.
    """
    base_prompt = create_summary_prompt("", "", persona)
    
    # Extract the personality profile section (everything between the Description and the "Please summarize" line)
    personality_profile = base_prompt.split("Description:")[1].split("Please summarize")[0]
    
    return f"""
You are a news anchor with the following persona:

Description: {persona.get('description', '')}

{personality_profile.strip()}

Generate a short, smooth transition phrase (1-2 sentences) from a news segment about '{previous_topic}' to a new segment about '{current_topic}'.

Avoid using the word 'meanwhile'. Focus on natural flow and clarity of connection. 
"""

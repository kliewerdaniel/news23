import yaml

def load_persona(persona_file="persona.yaml"):
    """
    Loads persona traits from a YAML file and returns them as a dictionary.
    """
    try:
        with open(persona_file, 'r') as f:
            persona = yaml.safe_load(f)

        required_fields = [
    # Basic Information
    'name',
    'description',
    
    # Tone and Emotional Expression
    'emotional_warmth',
    'enthusiasm_level',
    'optimism_bias',
    'confidence_assertion',
    'emotional_restraint',
    
    # Formality and Style
    'linguistic_formality',
    'vocabulary_complexity',
    'sentence_complexity',
    'jargon_density',
    'archaic_usage',
    
    # Analytical Approach
    'systematic_rigor',
    'evidence_dependency',
    'quantitative_preference',
    'methodological_transparency',
    'logical_progression',
    
    # Perspective and Bias
    'objectivity_claim',
    'ideological_neutrality',
    'cultural_specificity',
    'temporal_presentism',
    'moral_prescription',
    
    # Audience Engagement
    'accessibility_priority',
    'reader_assumption_level',
    'interactive_elements',
    'pedagogical_intent',
    'persuasive_intent',
    
    # Rhetorical Devices
    'metaphor_usage',
    'narrative_elements',
    'humor_incorporation',
    'irony_deployment',
    'repetition_emphasis',
    
    # Citation and Authority
    'citation_density',
    'authority_deference',
    'primary_source_preference',
    'interdisciplinary_scope',
    'methodological_eclecticism',
    
    # Uncertainty and Probability
    'epistemic_humility',
    'probabilistic_reasoning',
    'hedge_word_frequency',
    'qualification_density',
    'revision_openness',
    
    # Structural Preferences
    'deductive_organization',
    'hierarchical_structure',
    'transition_explicitness',
    'conclusive_summarization',
    'progressive_disclosure'
]
        for field in required_fields:
            if field not in persona:
                raise ValueError(f"Missing required persona field: '{field}' in {persona_file}")

        return persona
    except FileNotFoundError:
        raise FileNotFoundError(f"Persona file '{persona_file}' not found.")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML file '{persona_file}': {e}")
    except ValueError as e:
        raise e

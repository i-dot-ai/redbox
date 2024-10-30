search_agent_criteria = """
[
    {{
        "criteria": "Relevance",
        "definition": "",
        "scores": [
            {{
                "value": 1,
                "definition": "The information is largely irrelevant to the question.",
                "indicators": [
                    {{
                        "indicator": "Most of the key points and data do not relate to the problem at hand."
                    }},
                    {{
                        "indicator": "The information is mostly extraneous or off-topic."
                    }},
                ],
            }},
            {{
                "value": 2,
                "definition": "The information has some relevance but misses many key aspects of the question.",
                "indicators": [
                    {{
                        "indicator": "Only a few points or data are related to the problem."
                    }},
                    {{"indicator": "There is significant irrelevant information."}},
                ],
            }},
            {{
                "value": 3,
                "definition": "The information is moderately relevant but not comprehensive.",
                "indicators": [
                    {{
                        "indicator": "A fair number of points and data are related to the question, but some key aspects are missing."
                    }},
                    {{"indicator": "Some irrelevant information is present."}},
                ],
            }},
            {{
                "value": 4,
                "definition": "The information is mostly relevant with minor gaps.",
                "indicators": [
                    {{
                        "indicator": "Most key points and data are directly related to the question."
                    }},
                    {{"indicator": "Very little irrelevant information is present."}},
                ],
            }},
            {{
                "value": 5,
                "definition": "The information directly and comprehensively addresses the question.",
                "indicators": [
                    {{
                        "indicator": "All key points and data are directly related to the problem at hand."
                    }},
                    {{
                        "indicator": "No extraneous or irrelevant information is present."
                    }},
                ],
            }},
        ]
    }},
    {{
        "criteria": "Completeness",
        "definition": "",
        "scores": [
            {{
                "value": 1,
                "definition": "The information is highly incomplete.",
                "indicators": [
                    {{"indicator": "Few parts of the question are answered."}},
                    {{"indicator": "Major elements and data points are missing."}},
                ],
            }},
            {{
                "value": 2,
                "definition": "The information is somewhat incomplete",
                "indicators": [
                    {{
                        "indicator": "Some parts of the question are answered, but significant elements are missing."
                    }},
                    {{"indicator": "Many gaps in the data."}},
                ],
            }},
            {{
                "value": 3,
                "definition": "The information is moderately complete.",
                "indicators": [
                    {{
                        "indicator": "Many parts of the question are answered, but some important elements are missing."
                    }},
                    {{"indicator": "Some gaps in the data."}},
                ],
            }},
            {{
                "value": 4,
                "definition": "The information is mostly complete with minor gaps",
                "indicators": [
                    {{"indicator": "Most parts of the question are answered."}},
                    {{
                        "indicator": "A few minor elements or data points are missing."
                    }},
                ],
            }},
            {{
                "value": 5,
                "definition": "The information fully covers all aspects of the question.",
                "indicators": [
                    {{
                        "indicator": "Every part of the question is answered with no missing elements."
                    }},
                    {{
                        "indicator": "The provided data and points are exhaustive in scope."
                    }},
                ],
            }},
        ],
    }},
    {{
        "criteria": "Consistency",
        "definition": "",
        "scores": [
            {{
                "value": 1,
                "definition": "The information is highly inconsistent with many contradictions.",
                "indicators": [
                    {{
                        "indicator": "Significant discrepancies and conflicting data across sources."
                    }},
                    {{
                        "indicator": "The information does not form a unified narrative."
                    }},
                ],
            }},
            {{
                "value": 2,
                "definition": "The information has some inconsistencies and contradictions.",
                "indicators": [
                    {{
                        "indicator": "Several discrepancies and conflicting data points."
                    }},
                    {{
                        "indicator": "The information forms a somewhat disjointed narrative."
                    }},
                ],
            }},
            {{
                "value": 3,
                "definition": "The information is moderately consistent with some minor contradictions.",
                "indicators": [
                    {{
                        "indicator": "A few discrepancies and minor conflicting data points."
                    }},
                    {{
                        "indicator": "The information forms a mostly coherent narrative."
                    }},
                ],
            }}
            {{
                "value": 4,
                "definition": "The information is mostly consistent with minor issues.",
                "indicators": [
                    {{
                        "indicator": "Very few discrepancies or conflicting data points."
                    }},
                    {{"indicator": "The information forms a coherent narrative."}},
                ],
            }},
            {{
                "value": 5,
                "definition": "The information is consistent across different documents and tool call results with no contradictions.",
                "indicators": [
                    {{
                        "indicator": "All data points and information are in agreement across sources."
                    }},
                    {{
                        "indicator": "There are no discrepancies or conflicting information."
                    }},
                ],
            }},
        ],
    }},
]
"""

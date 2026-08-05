# server/rag_suggestions.py

class SmartSuggestions:
    """Generate contextual suggestions based on current data"""
    
    def get_suggestions(self, session_device_id: Optional[int] = None) -> Dict:
        """Get smart suggestions based on context"""
        
        # Quick action buttons
        quick_actions = [
            {"label": "High Engagement", "query": "high emotional engagement discussions"},
            {"label": "Analytical Moments", "query": "most analytical thinking"},
            {"label": "Equal Participation", "query": "balanced speaker participation"},
            {"label": "Compare Sessions", "query": "compare sessions"}
        ]
        
        # Contextual suggestions if viewing specific session
        contextual = []
        if session_device_id:
            contextual = [
                {"label": "Similar Sessions", "query": f"find sessions similar to device {session_device_id}"},
                {"label": "Timeline Analysis", "query": f"analyze device {session_device_id} over time"},
                {"label": "Key Patterns", "query": f"what patterns in device {session_device_id}"}
            ]
        
        # Example natural language queries
        examples = [
            "Why did engagement drop after minute 15?",
            "What triggers productive discussions?",
            "Show collaborative problem solving moments"
        ]
        
        return {
            "quick_actions": quick_actions,
            "contextual": contextual,
            "examples": examples,
            "placeholder": "Ask anything about your discussions..."
        }
# prompt_context.py

class PromptContext:
    """
    A simple data class to hold different layers of context for an agent's prompt.
    """
    def __init__(self):
        """
        Initializes the context holder with empty strings for background and current context.
        """
        self.background_briefing: str = ""
        self.current_context: str = ""

    def format_for_prompt(self) -> str:
        """
        Formats the stored context into a single string to be prepended to a user query.
        
        Returns:
            A formatted string containing the context, or an empty string if no context is set.
        """
        full_context = ""
        if self.background_briefing:
            full_context += f"--- Background Briefing ---\n{self.background_briefing}\n\n"
        
        if self.current_context:
            full_context += f"--- Current Context ---\n{self.current_context}\n\n"

        if full_context:
            return f"--- CONTEXT ---\n{full_context}--- USER QUERY ---\n"
        
        return ""

    def clear(self):
        """
        Resets both context attributes to empty strings.
        """
        self.background_briefing = ""
        self.current_context = ""


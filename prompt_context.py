# prompt_context.py

from collections import deque

class PromptContext:
    """
    A data class to hold different layers of context for an agent's prompt,
    including a rolling window of the most recent conversation messages.
    """
    def __init__(self, max_history_length: int = 5):
        """
        Initializes the context holder.

        Args:
            max_history_length: The maximum number of user/AI message pairs
                                to retain in the conversational history.
        """
        self.background_briefing: str = ""
        # Use a deque for efficient, rolling history.
        # This will store the last `max_history_length` exchanges (user + AI messages).
        self.history: deque[tuple[str, str]] = deque(maxlen=max_history_length * 2)

    def add_exchange(self, user_query: str, ai_response: str):
        """
        Adds a user query and the corresponding AI response to the history,
        maintaining the maximum history length.
        """
        self.history.append(("User", user_query))
        self.history.append(("AI", ai_response))

    def format_for_prompt(self) -> str:
        """
        Formats the stored context into a single string to be prepended to a user query.
        
        Returns:
            A formatted string containing the context, or an empty string if no context is set.
        """
        full_context = ""
        if self.background_briefing:
            full_context += f"--- Background Briefing ---\n{self.background_briefing}\n\n"
        
        if self.history:
            # Format the recent history from the deque
            history_str = "\n".join([f"{speaker}: {message}" for speaker, message in self.history])
            # The deque's maxlen is in terms of individual messages (user or AI), 
            # so we divide by 2 to get the number of exchanges.
            history_header = f"--- Recent Conversation History (last {self.history.maxlen // 2} exchanges) ---"
            full_context += f"{history_header}\n{history_str}\n\n"

        if full_context:
            return f"--- CONTEXT ---\n{full_context}--- USER QUERY ---\n"
        
        return ""

    def clear(self):
        """
        Resets the background briefing and clears the history.
        """
        self.background_briefing = ""
        self.history.clear()

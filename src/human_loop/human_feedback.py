from typing import Dict, List


class HumanFeedback:
    def __init__(self):
        self.feedbacks = {}

    def get_human_feedback(self, response: str, agent_name: str) -> Dict:
        """
        Get feedback from a human user for the given AI response.

        Args:
            response (str): The AI agent's response to get feedback for

        Returns:
            Dict: A dictionary containing either user feedback or a continue signal
        """
        print("\nATTENSION PLEASE")
        print(response)
        print(
            "\nDo you have any feedback? (Press Enter to continue without feedback)"
        )

        feedback = input("Your feedback: ").strip()

        if not feedback:
            return {"status": "continue", "feedback": None}
        else:
            try:
                self.feedbacks[agent_name].append(feedback)
            except KeyError:
                self.feedbacks[agent_name] = [feedback]

            return {"status": "feedback", "feedback": feedback}

    def get_feedbacks_for_agent(self, agent_name: str) -> List[str]:
        """
        Get feedback for the given agent
        """
        return self.feedbacks.get(agent_name, ["Not available"])


global_feedback_registry = HumanFeedback()

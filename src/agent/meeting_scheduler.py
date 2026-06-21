"""
Natural language meeting scheduling with calendar integration
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re
from dateutil import parser
from langchain.prompts import PromptTemplate
from langchain_community.llms import Ollama

logger = logging.getLogger(__name__)


class MeetingScheduler:
    """Schedule meetings via natural language"""

    def __init__(self, model_name: str = "llama3.2"):
        self.llm = Ollama(model=model_name)
        self.parse_prompt = PromptTemplate(
            input_variables=["request"],
            template="""Parse this meeting scheduling request and extract structured information.

Request: {request}

Extract the following in this exact format:
ATTENDEES: [email addresses]
DURATION: [number in minutes]
PREFERRED_DAY: [day of week or date]
PREFERRED_TIME: [morning/afternoon/evening or specific time]
TOPIC: [meeting topic/subject]
LOCATION: [physical location or "virtual"]

If information is not provided, use: UNKNOWN
"""
        )

    def schedule_meeting(
        self,
        prompt: str,
        organizer_email: str,
        calendar_api = None
    ) -> Dict:
        """
        Schedule a meeting from natural language prompt

        Args:
            prompt: Natural language scheduling request
            organizer_email: Email of the meeting organizer
            calendar_api: Calendar API client (Gmail/Outlook)

        Returns:
            Dict with meeting details and status
        """
        try:
            # Parse the request
            parsed = self._parse_meeting_request(prompt)

            # Find available time slot
            time_slot = self._find_time_slot(
                preferred_day=parsed.get('preferred_day'),
                preferred_time=parsed.get('preferred_time'),
                duration=parsed.get('duration', 30)
            )

            meeting_details = {
                "subject": parsed.get('topic', 'Meeting'),
                "start_time": time_slot['start'],
                "end_time": time_slot['end'],
                "attendees": parsed.get('attendees', []),
                "location": parsed.get('location', 'Virtual'),
                "organizer": organizer_email,
                "status": "scheduled"
            }

            # Create calendar event if API is provided
            if calendar_api:
                event_id = self._create_calendar_event(
                    calendar_api,
                    meeting_details
                )
                meeting_details['event_id'] = event_id
                meeting_details['invite_sent'] = True
            else:
                meeting_details['invite_sent'] = False

            logger.info(f"Scheduled meeting: {meeting_details['subject']} at {time_slot['start']}")

            return meeting_details

        except Exception as e:
            logger.error(f"Error scheduling meeting: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }

    def _parse_meeting_request(self, request: str) -> Dict:
        """Parse natural language meeting request"""
        try:
            prompt = self.parse_prompt.format(request=request)
            response = self.llm.invoke(prompt)

            parsed = {}
            for line in response.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()

                    if value != 'UNKNOWN':
                        if key == 'attendees':
                            # Extract email addresses
                            emails = re.findall(r'[\w\.-]+@[\w\.-]+', value)
                            parsed[key] = emails
                        elif key == 'duration':
                            # Extract number
                            duration = re.search(r'\d+', value)
                            parsed[key] = int(duration.group()) if duration else 30
                        else:
                            parsed[key] = value

            return parsed

        except Exception as e:
            logger.error(f"Error parsing meeting request: {e}")
            # Fallback: try regex extraction
            return self._regex_fallback_parse(request)

    def _regex_fallback_parse(self, request: str) -> Dict:
        """Fallback regex-based parsing"""
        parsed = {}

        # Extract emails
        emails = re.findall(r'[\w\.-]+@[\w\.-]+', request)
        if emails:
            parsed['attendees'] = emails

        # Extract duration
        duration_match = re.search(r'(\d+)\s*(min|minute|hour)', request, re.IGNORECASE)
        if duration_match:
            value = int(duration_match.group(1))
            unit = duration_match.group(2).lower()
            parsed['duration'] = value * 60 if 'hour' in unit else value

        # Extract day references
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for day in days:
            if day in request.lower():
                parsed['preferred_day'] = day
                break

        # Extract time references
        if 'morning' in request.lower():
            parsed['preferred_time'] = 'morning'
        elif 'afternoon' in request.lower():
            parsed['preferred_time'] = 'afternoon'
        elif 'evening' in request.lower():
            parsed['preferred_time'] = 'evening'

        return parsed

    def _find_time_slot(
        self,
        preferred_day: Optional[str],
        preferred_time: Optional[str],
        duration: int
    ) -> Dict:
        """
        Find available time slot

        Args:
            preferred_day: Day preference
            preferred_time: Time preference (morning/afternoon/evening)
            duration: Meeting duration in minutes

        Returns:
            Dict with start and end datetime
        """
        now = datetime.now()

        # Default to next business day if no preference
        if not preferred_day:
            # Skip to next weekday
            days_ahead = 1
            while (now + timedelta(days=days_ahead)).weekday() >= 5:
                days_ahead += 1
            target_date = now + timedelta(days=days_ahead)
        else:
            # Parse day reference
            target_date = self._parse_day_reference(preferred_day, now)

        # Set time based on preference
        if preferred_time == 'morning':
            hour = 10
        elif preferred_time == 'afternoon':
            hour = 14
        elif preferred_time == 'evening':
            hour = 17
        else:
            hour = 14  # Default to 2 PM

        start = target_date.replace(hour=hour, minute=0, second=0, microsecond=0)
        end = start + timedelta(minutes=duration)

        return {
            "start": start,
            "end": end
        }

    def _parse_day_reference(self, day_ref: str, from_date: datetime) -> datetime:
        """Parse day reference like 'next tuesday' into datetime"""
        day_ref = day_ref.lower()

        days = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }

        # Handle 'next [day]'
        for day_name, day_num in days.items():
            if day_name in day_ref:
                days_ahead = (day_num - from_date.weekday()) % 7
                if days_ahead == 0 and 'next' in day_ref:
                    days_ahead = 7
                return from_date + timedelta(days=days_ahead)

        # Try parsing as date
        try:
            return parser.parse(day_ref)
        except:
            # Default to tomorrow
            return from_date + timedelta(days=1)

    def _create_calendar_event(
        self,
        calendar_api,
        meeting_details: Dict
    ) -> str:
        """
        Create calendar event via API

        Args:
            calendar_api: Calendar API client
            meeting_details: Meeting information

        Returns:
            Event ID
        """
        # This is a placeholder for actual calendar API integration
        # Implementation would depend on Gmail Calendar API or Microsoft Graph

        logger.info(f"Creating calendar event: {meeting_details['subject']}")

        # Return mock event ID
        return f"event_{datetime.now().timestamp()}"

    def check_availability(
        self,
        calendar_api,
        start_time: datetime,
        end_time: datetime,
        attendees: List[str]
    ) -> Dict:
        """
        Check availability for all attendees

        Returns:
            Dict with availability status and conflicts
        """
        # Placeholder for actual availability check
        return {
            "available": True,
            "conflicts": [],
            "suggested_times": []
        }

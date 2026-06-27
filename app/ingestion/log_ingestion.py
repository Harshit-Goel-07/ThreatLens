"""
Security log ingestion for Security Copilot
Processes various security log formats (Sysmon, Windows Event, Linux auditd)
"""

import logging
import json
import re
from typing import Dict, Any, List, AsyncGenerator
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.ingestion.base import BaseIngestor, DocumentChunk
from app.ingestion.chunking import SemanticChunker

logger = logging.getLogger(__name__)


class SecurityLogIngestor(BaseIngestor):
    """Security log data ingestor"""
    
    def __init__(self, log_directory: str = "data/sample_logs"):
        super().__init__(source_type="logs")
        self.chunker = SemanticChunker(chunk_size=300, chunk_overlap=30)
        self.log_directory = Path(log_directory)
    
    async def fetch_data(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Fetch security logs from directory"""
        try:
            if not self.log_directory.exists():
                self.logger.warning(f"Log directory not found: {self.log_directory}")
                # Yield sample logs for testing
                for sample_log in self._get_sample_logs():
                    yield sample_log
                return
            
            # Process log files
            for log_file in self.log_directory.glob("*.json"):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        logs = json.load(f)
                        
                        if isinstance(logs, list):
                            for log in logs:
                                yield self._parse_log(log, log_file.stem)
                        else:
                            yield self._parse_log(logs, log_file.stem)
                            
                except Exception as e:
                    self.logger.error(f"Failed to read log file {log_file}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to fetch logs: {e}")
            raise
    
    def _parse_log(self, log_data: Dict[str, Any], log_type: str) -> Dict[str, Any]:
        """Parse log entry based on type"""
        # Detect log type if not specified
        if 'EventID' in log_data or 'EventId' in log_data:
            return self._parse_windows_event(log_data)
        elif 'Image' in log_data and 'CommandLine' in log_data:
            return self._parse_sysmon(log_data)
        elif 'type' in log_data and 'msg' in log_data:
            return self._parse_auditd(log_data)
        else:
            return self._parse_generic(log_data, log_type)
    
    def _parse_windows_event(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Windows Event Log"""
        event_id = log_data.get('EventID') or log_data.get('EventId', 0)
        
        return {
            'log_id': f"winevent_{event_id}_{hash(str(log_data))}",
            'log_type': 'windows_event',
            'event_id': str(event_id),
            'event_name': log_data.get('TaskDisplayName', 'Unknown Event'),
            'severity': self._map_windows_severity(log_data.get('Level', 0)),
            'category': log_data.get('Channel', 'Unknown'),
            'hostname': log_data.get('Computer', 'Unknown'),
            'username': log_data.get('SubjectUserName', 'Unknown'),
            'timestamp': log_data.get('TimeCreated', datetime.utcnow().isoformat()),
            'description': log_data.get('Message', ''),
            'raw_log': json.dumps(log_data, indent=2),
            'parsed_fields': log_data
        }
    
    def _parse_sysmon(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Sysmon log"""
        event_id = log_data.get('EventID', 0)
        
        return {
            'log_id': f"sysmon_{event_id}_{hash(str(log_data))}",
            'log_type': 'sysmon',
            'event_id': str(event_id),
            'event_name': self._get_sysmon_event_name(event_id),
            'severity': 'MEDIUM',
            'category': 'Process Monitoring',
            'hostname': log_data.get('Computer', 'Unknown'),
            'username': log_data.get('User', 'Unknown'),
            'process_name': log_data.get('Image', 'Unknown'),
            'command_line': log_data.get('CommandLine', ''),
            'timestamp': log_data.get('UtcTime', datetime.utcnow().isoformat()),
            'description': f"Process: {log_data.get('Image', 'Unknown')} - {log_data.get('CommandLine', '')}",
            'raw_log': json.dumps(log_data, indent=2),
            'parsed_fields': log_data
        }
    
    def _parse_auditd(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Linux auditd log"""
        return {
            'log_id': f"auditd_{hash(str(log_data))}",
            'log_type': 'auditd',
            'event_id': log_data.get('type', 'UNKNOWN'),
            'event_name': log_data.get('type', 'Unknown Event'),
            'severity': 'MEDIUM',
            'category': 'System Audit',
            'hostname': log_data.get('hostname', 'Unknown'),
            'username': log_data.get('uid', 'Unknown'),
            'timestamp': log_data.get('time', datetime.utcnow().isoformat()),
            'description': log_data.get('msg', ''),
            'raw_log': json.dumps(log_data, indent=2),
            'parsed_fields': log_data
        }
    
    def _parse_generic(self, log_data: Dict[str, Any], log_type: str) -> Dict[str, Any]:
        """Parse generic log format"""
        return {
            'log_id': f"{log_type}_{hash(str(log_data))}",
            'log_type': log_type,
            'event_id': 'GENERIC',
            'event_name': 'Generic Log Entry',
            'severity': 'INFO',
            'category': 'General',
            'hostname': log_data.get('host', 'Unknown'),
            'username': log_data.get('user', 'Unknown'),
            'timestamp': log_data.get('timestamp', datetime.utcnow().isoformat()),
            'description': str(log_data),
            'raw_log': json.dumps(log_data, indent=2),
            'parsed_fields': log_data
        }
    
    def _map_windows_severity(self, level: int) -> str:
        """Map Windows event level to severity"""
        severity_map = {
            1: 'CRITICAL',
            2: 'ERROR',
            3: 'WARNING',
            4: 'INFO',
            5: 'VERBOSE'
        }
        return severity_map.get(level, 'UNKNOWN')
    
    def _get_sysmon_event_name(self, event_id: int) -> str:
        """Get Sysmon event name from ID"""
        sysmon_events = {
            1: 'Process Creation',
            2: 'File Creation Time Changed',
            3: 'Network Connection',
            5: 'Process Terminated',
            7: 'Image Loaded',
            8: 'CreateRemoteThread',
            10: 'Process Access',
            11: 'File Created',
            12: 'Registry Event',
            13: 'Registry Value Set',
            22: 'DNS Query'
        }
        return sysmon_events.get(event_id, f'Sysmon Event {event_id}')
    
    def _get_sample_logs(self) -> List[Dict[str, Any]]:
        """Get sample security logs for testing"""
        return [
            {
                'EventID': 4624,
                'TaskDisplayName': 'Logon',
                'Level': 4,
                'Channel': 'Security',
                'Computer': 'WORKSTATION01',
                'SubjectUserName': 'admin',
                'TimeCreated': datetime.utcnow().isoformat(),
                'Message': 'An account was successfully logged on.'
            },
            {
                'EventID': 1,
                'Image': 'C:\\Windows\\System32\\cmd.exe',
                'CommandLine': 'cmd.exe /c whoami',
                'Computer': 'WORKSTATION01',
                'User': 'DOMAIN\\user',
                'UtcTime': datetime.utcnow().isoformat()
            }
        ]
    
    async def process_document(self, raw_doc: Dict[str, Any]) -> List[DocumentChunk]:
        """Process security log into chunks"""
        try:
            doc_id = raw_doc['log_id']
            
            # Create content for chunking
            content = f"""
Log Type: {raw_doc['log_type']}
Event ID: {raw_doc['event_id']}
Event: {raw_doc['event_name']}
Severity: {raw_doc['severity']}
Timestamp: {raw_doc['timestamp']}
Host: {raw_doc.get('hostname', 'Unknown')}
User: {raw_doc.get('username', 'Unknown')}

Description:
{raw_doc['description']}

{f"Process: {raw_doc.get('process_name', '')}" if raw_doc.get('process_name') else ""}
{f"Command Line: {raw_doc.get('command_line', '')}" if raw_doc.get('command_line') else ""}
"""
            
            # Chunk the content
            chunks = self.chunker.chunk_text(content.strip(), preserve_structure=False)
            
            # Convert to DocumentChunk objects
            document_chunks = []
            for chunk in chunks:
                doc_chunk = DocumentChunk(
                    chunk_id=f"{doc_id}_chunk_{chunk['chunk_index']}",
                    doc_id=doc_id,
                    content=chunk['content'],
                    metadata={
                        'source_type': 'logs',
                        'log_type': raw_doc['log_type'],
                        'event_id': raw_doc['event_id'],
                        'event_name': raw_doc['event_name'],
                        'severity': raw_doc['severity'],
                        'hostname': raw_doc.get('hostname'),
                        'timestamp': raw_doc['timestamp']
                    },
                    source_type='logs',
                    chunk_index=chunk['chunk_index'],
                    total_chunks=len(chunks)
                )
                document_chunks.append(doc_chunk)
            
            return document_chunks
            
        except Exception as e:
            self.logger.error(f"Failed to process security log: {e}")
            return []
    
    async def validate_document(self, raw_doc: Dict[str, Any]) -> bool:
        """Validate security log document"""
        required_fields = ['log_id', 'log_type', 'event_id']
        
        for field in required_fields:
            if not raw_doc.get(field):
                self.logger.warning(f"Missing required field: {field}")
                return False
        
        return True
    
    def extract_metadata(self, raw_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from security log"""
        return {
            'log_id': raw_doc.get('log_id'),
            'log_type': raw_doc.get('log_type'),
            'event_id': raw_doc.get('event_id'),
            'event_name': raw_doc.get('event_name'),
            'severity': raw_doc.get('severity'),
            'hostname': raw_doc.get('hostname'),
            'username': raw_doc.get('username'),
            'timestamp': raw_doc.get('timestamp')
        }


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)
    asyncio.run(SecurityLogIngestor().ingest())

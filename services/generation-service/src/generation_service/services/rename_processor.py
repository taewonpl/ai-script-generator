"""
Enhanced rename processing with word boundaries and cycle detection.
Provides safe and consistent character/entity name replacement.
"""

import re
import logging
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RenameConflict:
    """Information about a rename conflict"""
    
    original_name: str
    target_name: str
    conflict_type: str  # 'cycle', 'overlap', 'boundary'
    description: str


class SafeRenameProcessor:
    """Safe rename processing with cycle detection and word boundaries"""
    
    def __init__(self):
        # Korean particle patterns for morphological awareness
        self.korean_particles = [
            '이', '가', '을', '를', '은', '는', '와', '과', '에', '에서', '로', '으로',
            '의', '도', '만', '까지', '부터', '처럼', '같이', '보다', '한테', '께',
            '이나', '나', '라도', '든지', '이든', '든', '이야', '야', '이여', '여'
        ]
        
        # Compile Korean particle regex for efficiency
        particle_pattern = '|'.join(re.escape(p) for p in self.korean_particles)
        self.korean_particle_regex = re.compile(f'({particle_pattern})(?=\\s|$|[^가-힣])', re.UNICODE)
        
    def detect_rename_cycles(self, rename_map: Dict[str, str]) -> List[List[str]]:
        """Detect cycles in rename mapping"""
        
        def find_cycle_from_node(start: str, visited: Set[str], path: List[str]) -> Optional[List[str]]:
            if start in visited:
                # Found a cycle, return the cycle portion
                cycle_start = path.index(start)
                return path[cycle_start:]
            
            if start not in rename_map:
                return None
                
            visited.add(start)
            path.append(start)
            
            next_node = rename_map[start]
            result = find_cycle_from_node(next_node, visited, path)
            
            if result:
                return result
                
            visited.remove(start)
            path.pop()
            return None
        
        cycles = []
        global_visited = set()
        
        for start_node in rename_map:
            if start_node not in global_visited:
                cycle = find_cycle_from_node(start_node, set(), [])
                if cycle:
                    cycles.append(cycle)
                    global_visited.update(cycle)
        
        return cycles
    
    def validate_rename_map(self, rename_map: Dict[str, str]) -> Tuple[bool, List[RenameConflict]]:
        """Validate rename map for conflicts and cycles"""
        
        conflicts = []
        
        # Check for cycles
        cycles = self.detect_rename_cycles(rename_map)
        for cycle in cycles:
            conflicts.append(RenameConflict(
                original_name=cycle[0],
                target_name=cycle[-1],
                conflict_type='cycle',
                description=f"Rename cycle detected: {' → '.join(cycle + [cycle[0]])}"
            ))
        
        # Check for overlapping names that might cause confusion
        all_names = set(rename_map.keys()) | set(rename_map.values())
        
        for original, target in rename_map.items():
            # Check if target name is substring of another name (potential overlap)
            for other_name in all_names:
                if other_name != target and other_name != original:
                    if target.lower() in other_name.lower() and len(target) < len(other_name):
                        conflicts.append(RenameConflict(
                            original_name=original,
                            target_name=target,
                            conflict_type='overlap',
                            description=f"Name '{target}' overlaps with existing name '{other_name}'"
                        ))
        
        is_valid = len(conflicts) == 0
        return is_valid, conflicts
    
    def apply_word_boundary_replacement(self, text: str, original: str, target: str) -> str:
        """Apply replacement with proper word boundaries"""
        
        # Escape special regex characters in names
        escaped_original = re.escape(original)
        
        # Create word boundary pattern
        # For Korean text, we need to be more careful about boundaries
        if self._contains_korean(original):
            # Korean word boundary: space, punctuation, or particle
            pattern = f'\\b{escaped_original}(?=\\s|[,.!?;:]|{"|".join(re.escape(p) for p in self.korean_particles)}|$)'
        else:
            # English word boundary
            pattern = f'\\b{escaped_original}\\b'
        
        # Apply replacement with case preservation for English
        if self._is_english_name(original):
            return self._case_preserving_replace(text, pattern, original, target)
        else:
            return re.sub(pattern, target, text, flags=re.IGNORECASE | re.UNICODE)
    
    def process_content_with_renames(self, content: str, rename_map: Dict[str, str], 
                                   selection_range: Optional[Tuple[int, int]] = None) -> Tuple[str, List[str]]:
        """
        Process content with safe rename replacements
        
        Args:
            content: Text content to process
            rename_map: Mapping of old names to new names
            selection_range: If provided, only apply renames within this character range
            
        Returns:
            Tuple of (processed_content, warnings)
        """
        
        warnings = []
        
        # Validate rename map first
        is_valid, conflicts = self.validate_rename_map(rename_map)
        if not is_valid:
            for conflict in conflicts:
                warnings.append(f"Rename conflict: {conflict.description}")
                logger.warning(f"Rename conflict detected: {conflict}")
            
            # Filter out conflicting renames
            safe_rename_map = self._filter_conflicting_renames(rename_map, conflicts)
        else:
            safe_rename_map = rename_map
        
        # Apply renames in order of name length (longest first to avoid partial replacements)
        sorted_renames = sorted(safe_rename_map.items(), key=lambda x: len(x[0]), reverse=True)
        
        processed_content = content
        
        for original, target in sorted_renames:
            if original.strip() and target.strip() and original != target:
                try:
                    if selection_range:
                        # Only apply rename within selection range
                        before_selection = processed_content[:selection_range[0]]
                        selection_content = processed_content[selection_range[0]:selection_range[1]]
                        after_selection = processed_content[selection_range[1]:]
                        
                        # Apply rename only to selection
                        processed_selection = self.apply_word_boundary_replacement(
                            selection_content, original, target
                        )
                        
                        processed_content = before_selection + processed_selection + after_selection
                    else:
                        # Apply rename to entire content
                        processed_content = self.apply_word_boundary_replacement(
                            processed_content, original, target
                        )
                        
                except re.error as e:
                    warning = f"Failed to apply rename '{original}' → '{target}': {e}"
                    warnings.append(warning)
                    logger.error(warning)
        
        return processed_content, warnings
    
    def _filter_conflicting_renames(self, rename_map: Dict[str, str], 
                                  conflicts: List[RenameConflict]) -> Dict[str, str]:
        """Filter out conflicting renames to create a safe mapping"""
        
        conflicting_names = set()
        for conflict in conflicts:
            if conflict.conflict_type == 'cycle':
                conflicting_names.add(conflict.original_name)
            elif conflict.conflict_type == 'overlap':
                # Remove the shorter name in overlapping conflicts
                if len(conflict.target_name) < len(conflict.original_name):
                    conflicting_names.add(conflict.original_name)
        
        safe_map = {k: v for k, v in rename_map.items() if k not in conflicting_names}
        
        if len(safe_map) < len(rename_map):
            logger.info(f"Filtered {len(rename_map) - len(safe_map)} conflicting renames")
        
        return safe_map
    
    def _contains_korean(self, text: str) -> bool:
        """Check if text contains Korean characters"""
        return bool(re.search(r'[가-힣]', text))
    
    def _is_english_name(self, name: str) -> bool:
        """Check if name is primarily English"""
        return bool(re.match(r'^[A-Za-z\s\-\.]+$', name))
    
    def _case_preserving_replace(self, text: str, pattern: str, original: str, target: str) -> str:
        """Replace with case preservation for English names"""
        
        def replace_match(match):
            matched_text = match.group(0)
            
            # Preserve original casing pattern
            if matched_text.isupper():
                return target.upper()
            elif matched_text.islower():
                return target.lower()
            elif matched_text.istitle():
                return target.title()
            else:
                return target
        
        return re.sub(pattern, replace_match, text, flags=re.UNICODE)
    
    def preview_renames(self, content: str, rename_map: Dict[str, str]) -> Dict[str, List[Tuple[int, int, str]]]:
        """Preview where renames would be applied"""
        
        preview = {}
        
        for original, target in rename_map.items():
            if original.strip() and target.strip() and original != target:
                matches = []
                
                # Find all matches with word boundaries
                if self._contains_korean(original):
                    pattern = f'\\b{re.escape(original)}(?=\\s|[,.!?;:]|$)'
                else:
                    pattern = f'\\b{re.escape(original)}\\b'
                
                try:
                    for match in re.finditer(pattern, content, re.IGNORECASE | re.UNICODE):
                        matches.append((match.start(), match.end(), match.group(0)))
                    
                    if matches:
                        preview[f"{original} → {target}"] = matches
                        
                except re.error:
                    continue
        
        return preview
    
    def get_rename_statistics(self, content: str, rename_map: Dict[str, str]) -> Dict[str, int]:
        """Get statistics about rename operations"""
        
        stats = {
            'total_renames': len(rename_map),
            'applicable_renames': 0,
            'total_replacements': 0,
            'korean_names': 0,
            'english_names': 0,
        }
        
        for original, target in rename_map.items():
            if original.strip() and target.strip() and original != target:
                # Count character types
                if self._contains_korean(original):
                    stats['korean_names'] += 1
                elif self._is_english_name(original):
                    stats['english_names'] += 1
                
                # Count potential replacements
                if self._contains_korean(original):
                    pattern = f'\\b{re.escape(original)}(?=\\s|[,.!?;:]|$)'
                else:
                    pattern = f'\\b{re.escape(original)}\\b'
                
                try:
                    matches = len(re.findall(pattern, content, re.IGNORECASE | re.UNICODE))
                    if matches > 0:
                        stats['applicable_renames'] += 1
                        stats['total_replacements'] += matches
                except re.error:
                    continue
        
        return stats


# Global instance for reuse
_rename_processor = SafeRenameProcessor()


def process_renames_safely(content: str, rename_map: Dict[str, str], 
                         selection_range: Optional[Tuple[int, int]] = None) -> Tuple[str, List[str]]:
    """Convenience function for safe rename processing"""
    return _rename_processor.process_content_with_renames(content, rename_map, selection_range)


def validate_renames(rename_map: Dict[str, str]) -> Tuple[bool, List[str]]:
    """Convenience function for rename validation"""
    is_valid, conflicts = _rename_processor.validate_rename_map(rename_map)
    conflict_messages = [conflict.description for conflict in conflicts]
    return is_valid, conflict_messages


def preview_rename_locations(content: str, rename_map: Dict[str, str]) -> Dict[str, List[Tuple[int, int, str]]]:
    """Convenience function for rename preview"""
    return _rename_processor.preview_renames(content, rename_map)
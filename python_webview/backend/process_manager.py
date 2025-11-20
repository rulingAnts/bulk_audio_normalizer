"""
Process manager for handling FFmpeg subprocesses with proper cleanup.

This module provides better subprocess management than the Electron version,
with reliable process tree killing and cleanup.
"""
import os
import signal
import subprocess
import psutil
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


class ProcessManager:
    """Manages FFmpeg subprocesses with proper cleanup."""
    
    def __init__(self):
        self.active_processes = {}  # job_id -> list of Popen objects
        self.cancel_all = False
        
    def spawn(self, cmd: List[str], job_id: Optional[str] = None, **kwargs) -> subprocess.Popen:
        """
        Spawn a subprocess with proper tracking.
        
        Args:
            cmd: Command and arguments to execute
            job_id: Optional job ID for tracking
            **kwargs: Additional arguments for subprocess.Popen
            
        Returns:
            subprocess.Popen object
        """
        # Create new process group on Unix, CREATE_NEW_PROCESS_GROUP on Windows
        if os.name == 'nt':  # Windows
            # CREATE_NO_WINDOW = 0x08000000
            # CREATE_NEW_PROCESS_GROUP = 0x00000200
            creation_flags = kwargs.pop('creationflags', 0)
            creation_flags |= 0x08000000 | 0x00000200
            kwargs['creationflags'] = creation_flags
        else:  # Unix-like
            kwargs['start_new_session'] = True
            
        # Ensure we can capture output
        if 'stdout' not in kwargs:
            kwargs['stdout'] = subprocess.PIPE
        if 'stderr' not in kwargs:
            kwargs['stderr'] = subprocess.PIPE
            
        proc = subprocess.Popen(cmd, **kwargs)
        
        # Track the process
        if job_id:
            if job_id not in self.active_processes:
                self.active_processes[job_id] = []
            self.active_processes[job_id].append(proc)
            
        logger.debug(f"Spawned process {proc.pid} for job {job_id}")
        return proc
        
    def kill_process_tree(self, proc: subprocess.Popen) -> None:
        """
        Kill a process and all its children.
        
        This is more reliable than the Electron version because Python's psutil
        can properly enumerate and kill all child processes.
        
        Args:
            proc: Process to kill
        """
        if not proc or not proc.pid:
            return
            
        try:
            parent = psutil.Process(proc.pid)
            children = parent.children(recursive=True)
            
            # Kill children first
            for child in children:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
                    
            # Kill parent
            try:
                parent.kill()
            except psutil.NoSuchProcess:
                pass
                
            # Wait for processes to die
            gone, alive = psutil.wait_procs(children + [parent], timeout=3)
            
            # Force kill any survivors
            for p in alive:
                try:
                    p.kill()
                except psutil.NoSuchProcess:
                    pass
                    
            logger.debug(f"Killed process tree for PID {proc.pid}")
            
        except psutil.NoSuchProcess:
            logger.debug(f"Process {proc.pid} already dead")
        except Exception as e:
            logger.error(f"Error killing process tree {proc.pid}: {e}")
            # Fallback to simple kill
            try:
                proc.kill()
            except:
                pass
                
    def kill_job(self, job_id: str) -> None:
        """
        Kill all processes associated with a job.
        
        Args:
            job_id: Job ID to kill
        """
        if job_id not in self.active_processes:
            return
            
        processes = self.active_processes[job_id]
        for proc in processes:
            self.kill_process_tree(proc)
            
        del self.active_processes[job_id]
        logger.info(f"Killed all processes for job {job_id}")
        
    def kill_all(self) -> None:
        """Kill all tracked processes."""
        self.cancel_all = True
        job_ids = list(self.active_processes.keys())
        for job_id in job_ids:
            self.kill_job(job_id)
        logger.info("Killed all processes")
        
    def cleanup_job(self, job_id: str) -> None:
        """
        Clean up finished processes for a job.
        
        Args:
            job_id: Job ID to clean up
        """
        if job_id in self.active_processes:
            # Remove finished processes
            self.active_processes[job_id] = [
                p for p in self.active_processes[job_id]
                if p.poll() is None
            ]
            # Remove job if no processes left
            if not self.active_processes[job_id]:
                del self.active_processes[job_id]
                
    def is_canceled(self, job_id: Optional[str] = None) -> bool:
        """
        Check if processing should be canceled.
        
        Args:
            job_id: Optional job ID to check
            
        Returns:
            True if canceled
        """
        return self.cancel_all


# Global process manager instance
process_manager = ProcessManager()

"""
Database Service - Handles database operations for postal codes and other data.
Provides a clean interface for database interactions.
"""

import os
from typing import Optional, List, Tuple, Dict, Any
from loguru import logger

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    logger.warning("⚠️ psycopg2 not available - database operations will be disabled")


class DatabaseService:
    """
    Service for database operations.
    Provides connection pooling and query execution.
    """
    
    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize the database service.
        
        Args:
            connection_string: PostgreSQL connection string
        """
        self.connection_string = connection_string or os.getenv(
            'DATABASE_CONNECTION_STRING',
            "postgresql://postgres.jluuralqpnexhxlcuewz:HIiamjami1234@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"
        )
        
        if not PSYCOPG2_AVAILABLE:
            logger.warning("⚠️ Database service initialized without psycopg2 - operations will fail")
        else:
            logger.info("✅ Database service initialized")
    
    def get_connection(self):
        """
        Get a database connection.
        
        Returns:
            psycopg2 connection object
        """
        if not PSYCOPG2_AVAILABLE:
            raise Exception("psycopg2 not available")
        
        try:
            conn = psycopg2.connect(self.connection_string)
            return conn
        except Exception as e:
            logger.error(f"❌ Database connection error: {e}")
            raise
    
    def execute_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        fetch: bool = True
    ) -> Optional[List[tuple]]:
        """
        Execute a SQL query.
        
        Args:
            query: SQL query string
            params: Query parameters
            fetch: Whether to fetch results
            
        Returns:
            Query results or None
        """
        if not PSYCOPG2_AVAILABLE:
            logger.error("❌ Cannot execute query - psycopg2 not available")
            return None
        
        conn = None
        cursor = None
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(query, params)
            
            if fetch:
                results = cursor.fetchall()
                conn.commit()
                return results
            else:
                conn.commit()
                return None
                
        except Exception as e:
            logger.error(f"❌ Query execution error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def execute_query_dict(
        self,
        query: str,
        params: Optional[tuple] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a query and return results as dictionaries.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of result dictionaries or None
        """
        if not PSYCOPG2_AVAILABLE:
            logger.error("❌ Cannot execute query - psycopg2 not available")
            return None
        
        conn = None
        cursor = None
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # Convert to list of dicts
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"❌ Query execution error: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_postal_code(self, postcode: str) -> Optional[Dict[str, Any]]:
        """
        Get postal code information from database.
        
        Args:
            postcode: Postcode to look up
            
        Returns:
            Postal code data dictionary or None
        """
        query = 'SELECT * FROM postal_code WHERE "Postcode" = %s LIMIT 1;'
        
        try:
            results = self.execute_query_dict(query, (postcode,))
            if results and len(results) > 0:
                return results[0]
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching postal code {postcode}: {e}")
            return None
    
    def search_postal_codes(
        self,
        search_term: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search for postal codes by pattern.
        
        Args:
            search_term: Search pattern
            limit: Maximum results to return
            
        Returns:
            List of matching postal codes
        """
        query = '''
            SELECT * FROM postal_code 
            WHERE "Postcode" ILIKE %s 
            ORDER BY "Postcode" 
            LIMIT %s;
        '''
        
        try:
            # Add wildcards for LIKE search
            pattern = f"%{search_term}%"
            results = self.execute_query_dict(query, (pattern, limit))
            return results or []
        except Exception as e:
            logger.error(f"❌ Error searching postal codes: {e}")
            return []
    
    def get_table_structure(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get the structure of a database table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information dictionaries
        """
        query = """
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position;
        """
        
        try:
            results = self.execute_query_dict(query, (table_name,))
            return results or []
        except Exception as e:
            logger.error(f"❌ Error getting table structure for {table_name}: {e}")
            return []
    
    def get_table_count(self, table_name: str) -> int:
        """
        Get the number of rows in a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Row count
        """
        query = f'SELECT COUNT(*) FROM {table_name};'
        
        try:
            results = self.execute_query(query)
            if results and len(results) > 0:
                return results[0][0]
            return 0
        except Exception as e:
            logger.error(f"❌ Error counting rows in {table_name}: {e}")
            return 0
    
    def get_sample_data(
        self,
        table_name: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get sample rows from a table.
        
        Args:
            table_name: Name of the table
            limit: Number of rows to return
            
        Returns:
            List of sample rows
        """
        query = f'SELECT * FROM {table_name} LIMIT %s;'
        
        try:
            results = self.execute_query_dict(query, (limit,))
            return results or []
        except Exception as e:
            logger.error(f"❌ Error getting sample data from {table_name}: {e}")
            return []
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test the database connection.
        
        Returns:
            Tuple of (success, message)
        """
        if not PSYCOPG2_AVAILABLE:
            return False, "psycopg2 not available"
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT NOW();")
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return True, f"Connection successful. Server time: {result[0]}"
            
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
    
    def insert_data(
        self,
        table_name: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        Insert data into a table.
        
        Args:
            table_name: Name of the table
            data: Dictionary of column: value pairs
            
        Returns:
            True if successful, False otherwise
        """
        if not data:
            logger.warning("⚠️ No data provided for insert")
            return False
        
        columns = ', '.join(f'"{col}"' for col in data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        values = tuple(data.values())
        
        query = f'INSERT INTO {table_name} ({columns}) VALUES ({placeholders});'
        
        try:
            self.execute_query(query, values, fetch=False)
            logger.info(f"✅ Inserted data into {table_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Error inserting data into {table_name}: {e}")
            return False
    
    def batch_insert_data(
        self,
        table_name: str,
        data_list: List[Dict[str, Any]]
    ) -> int:
        """
        Batch insert multiple rows.
        
        Args:
            table_name: Name of the table
            data_list: List of data dictionaries
            
        Returns:
            Number of successful inserts
        """
        if not data_list:
            logger.warning("⚠️ No data provided for batch insert")
            return 0
        
        success_count = 0
        
        for data in data_list:
            if self.insert_data(table_name, data):
                success_count += 1
        
        logger.info(f"✅ Batch insert completed: {success_count}/{len(data_list)} successful")
        return success_count


# Global instance for easy access
_database_service = None


def get_database_service(connection_string: Optional[str] = None) -> DatabaseService:
    """
    Get or create the global database service instance.
    
    Args:
        connection_string: Optional database connection string
        
    Returns:
        DatabaseService instance
    """
    global _database_service
    if _database_service is None:
        _database_service = DatabaseService(connection_string)
    return _database_service


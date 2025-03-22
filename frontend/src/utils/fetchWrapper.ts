let csrfToken: string | null = null;

const getCsrfToken = async () => {
    if (!csrfToken) {
        try {
            const response = await fetch('/api/method/epibus.api.get_csrf_token');
            if (!response.ok) {
                throw new Error('Failed to fetch CSRF token');
            }
            const data = await response.json();
            if (!data.message?.csrf_token) {
                throw new Error('Invalid CSRF token response');
            }
            csrfToken = data.message.csrf_token;
        } catch (error) {
            console.error('Error fetching CSRF token:', error);
            throw new Error('Failed to obtain CSRF token');
        }
    }
    return csrfToken;
};

export const fetchWrapper = async (url: string, options?: RequestInit) => {
    try {
        const token = await getCsrfToken();
        if (!token) {
            throw new Error('No CSRF token available');
        }
        
        const headers = {
            'Content-Type': 'application/json',
            'X-Frappe-CSRF-Token': token,
            ...options?.headers,
        };

        const response = await fetch(url, {
            ...options,
            headers,
            credentials: 'same-origin'
        });

        // First check if response is ok
        if (!response.ok) {
            // Try to get error message from response if possible
            try {
                const errorData = await response.json();
                throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
            } catch {
                // If can't parse JSON, use status text
                throw new Error(`HTTP error! status: ${response.status} ${response.statusText}`);
            }
        }

        // Now we know response is ok, try to parse JSON
        const data = await response.json();

        // Check for Frappe-specific error formats in successful responses
        if (data.message?.status === 'error') {
            throw new Error(data.message.message || 'An error occurred');
        }

        return data;
    } catch (error: unknown) {
        console.error('Fetch error:', error);
        throw new Error(
            error instanceof Error 
                ? error.message 
                : 'An error occurred while fetching data'
        );
    }
};
import { useEffect, useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'

export function APITest() {
  const [result, setResult] = useState<string>('Testing connection...')

  useEffect(() => {
    // Use the proxied path instead of direct localhost:8000
    fetch('/api/method/frappe.auth.get_logged_user', {
      credentials: 'include'
    })
      .then(response => response.json())
      .then(data => {
        setResult(`Success: ${JSON.stringify(data)}`)
      })
      .catch(error => {
        setResult(`Error: ${error.message}`)
      })
  }, [])

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="text-lg font-semibold mb-4">Frappe API Test</h2>
        <pre className="bg-gray-100 p-4 rounded">
          {result}
        </pre>
      </CardContent>
    </Card>
  )
}
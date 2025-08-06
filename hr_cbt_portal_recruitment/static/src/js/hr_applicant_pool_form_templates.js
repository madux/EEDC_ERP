document.addEventListener('DOMContentLoaded', function () {
    // Get user's IP address and set applied date
    fetch('https://api.ipify.org?format=json')
        .then(response => response.json())
        .then(data => {
            document.getElementById('applicant_ipaddress').value = data.ip;
        })
        .catch(error => {
            console.log('Could not fetch IP address:', error);
        });

    // Set current date
    const today = new Date().toISOString().split('T')[0];
    document.querySelector('input[name="applied_date"]').value = today;

    // Form submission handler
    document.getElementById('applicationForm').addEventListener('submit', function (e) {
        e.preventDefault();

        const ipAddress = document.getElementById('applicant_ipaddress').value;
        const submitBtn = document.getElementById('submitBtn');

        if (!ipAddress) {
            alert('Unable to determine IP address. Please refresh and try again.');
            return;
        }

        // Disable submit button
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Checking...';

        // Check IP address restriction
        fetch('/applicant-pool-form/check_ipaddress', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'ip_address': ipAddress
                }
            })
        })
            .then(response => response.json())
            .then(data => {
                if (data.result && data.result.restricted) {
                    // Show restriction alert
                    document.getElementById('ip-alert').style.display = 'block';
                    document.getElementById('ip-alert').scrollIntoView({ behavior: 'smooth' });

                    // Re-enable submit button
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fa fa-paper-plane"></i> Submit Application';
                } else {
                    // Proceed with form submission
                    this.submit();
                }
            })
            .catch(error => {
                console.error('Error checking IP address:', error);
                // Proceed with form submission on error
                this.submit();
            });
    });

    // Check IP on page load for "Submit Another" scenario
    checkIPRestrictionOnLoad();
});

function checkIPRestrictionOnLoad() {
    fetch('https://api.ipify.org?format=json')
        .then(response => response.json())
        .then(data => {
            return fetch('/applicant-pool-form/check_ipaddress', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    'jsonrpc': '2.0',
                    'method': 'call',
                    'params': {
                        'ip_address': data.ip
                    }
                })
            });
        })
        .then(response => response.json())
        .then(data => {
            if (data.result && data.result.restricted) {
                // Show restriction alert and disable form
                document.getElementById('ip-alert').style.display = 'block';
                document.getElementById('submitBtn').disabled = true;
                document.getElementById('submitBtn').innerHTML = 'Submission Restricted';
                document.getElementById('submitBtn').style.background = '#95a5a6';
            }
        })
        .catch(error => {
            console.log('Error checking IP restriction on load:', error);
        });
}

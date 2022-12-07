// Add truncate func to String
String.prototype.truncate = String.prototype.truncate || 
    function ( n, useWordBoundary ){
    if (this.length <= n) { return this; }
    const subString = this.slice(0, n-1); // the original check
    return (useWordBoundary 
        ? subString.slice(0, subString.lastIndexOf(" ")) 
        : subString) + "&hellip;";
};

// Main function to make request and process response
function processSearch(query) {  
    // Safety wrap all processing
    try {
        fetch(
            `/process`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                redirect: 'follow',
                body: JSON.stringify({'query': query}),
            }
        ).then((response) => {
            response.json().then((data) => {
                // Catch error and redirect
                if ('error' in data) {
                    window.location.replace('/processing-error');
                };

                // Otherwise update DOM
                console.log('Found repos:', data);

                // Replace content in top statement
                topStatement.innerHTML = topStatement.innerHTML.replace(
                    'Finding possible repositories for paper:',
                    `${data.length} potential repositories for:`
                );

                // Remove loading div
                loadingDiv.parentNode.removeChild(loadingDiv);

                // Add other matches content
                loadedContentDiv.querySelector('#all-other-matches-header').innerHTML = "Other Matches"

                // Process each repo found
                let templateClone;
                data.forEach((repo_data, index) => {
                    // Get the template for the best match
                    if (index == 0) {
                        templateClone = bestMatchTemplate.content.cloneNode(true);
                    // Get the repeatable template for all other matches
                    } else {
                        templateClone = repeatRepoMatchTemplate.content.cloneNode(true);
                    }

                    // Fill in basic details
                    templateClone.querySelector('.repo-name').innerHTML = repo_data['name'];
                    if (repo_data['description']) {
                        templateClone.querySelector('.repo-description').innerHTML = repo_data['description'].truncate(256, true);
                    };
                    templateClone.querySelector('.repo-link').href = repo_data['link'];

                    // Generate repo stats div
                    let resultRepoStatsClone = resultRepoStatsTemplate.content.cloneNode(true);
                    resultRepoStatsClone.querySelector('.star-count').innerHTML = repo_data['stars'];
                    resultRepoStatsClone.querySelector('.watcher-count').innerHTML = repo_data['watchers'];
                    resultRepoStatsClone.querySelector('.fork-count').innerHTML = repo_data['forks'];
                    resultRepoStatsClone.querySelector('.query-details').innerHTML = `found from search for '${repo_data['search_query']}'`;

                    // Attach repo stats to template clone
                    templateClone.querySelector('.repo-stats-container').appendChild(resultRepoStatsClone);

                    // Insert best match
                    if (index === 0) {
                        bestMatchDiv.appendChild(templateClone);
                    // Insert all others
                    } else {
                        allOtherMatchesDiv.appendChild(templateClone);
                    };
                });
            });
        });
    } catch {
        window.location.replace('/processing-error');
    }
};
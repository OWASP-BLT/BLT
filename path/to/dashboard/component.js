import React from 'react';
import { useFetch } from 'some-fetch-hook';

const Dashboard = () => {
    const { data, error } = useFetch('/api/social-stats');

    if (error) return <div>Error loading stats</div>;

    return (
        <div>
            <h2>Social Stats</h2>
            <p>Stars: {data.stars}</p>
            <p>Forks: {data.forks}</p>
            <p>Contributors: {data.contributors}</p>
        </div>
    );
};

export default Dashboard;
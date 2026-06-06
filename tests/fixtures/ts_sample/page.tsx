import React from 'react';
import { useState, useEffect } from 'react';
import { Button } from '@/components/ui';

export default function HomePage() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    console.log('mounted');
  }, []);

  return (
    <div>
      <Button onClick={() => setCount(c => c + 1)}>
        Clicked {count} times
      </Button>
      <Component />
    </div>
  );
}

interface Props {
  title: string;
}

class MyComponent extends React.Component<Props> {
  render() {
    return <span>{this.props.title}</span>;
  }
}

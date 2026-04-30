/**
 * Lesson Catalogue
 * Central source of truth for all available lessons and their content
 * Organized by subject → topic → slides
 */

export const LESSON_CATALOGUE = [
  {
    subject: 'Math',
    subjectId: 'math',
    descriptor: 'Geometry & Trigonometry',
    topics: [
      {
        topicId: 'pythagoras',
        title: "Pythagoras' Theorem",
        duration: '20 min',
        lessonContent: {
          slides: [
            {
              heading: "What is Pythagoras' Theorem?",
              body: `In any right-angled triangle, the square of the longest side (the hypotenuse) 
equals the sum of the squares of the other two sides. We write this as: a² + b² = c², 
where c is always the hypotenuse — the side opposite the right angle. This relationship 
holds true for every right-angled triangle, no matter the size.`
            },
            {
              heading: 'A Simple Example',
              body: `Imagine a right-angled triangle where one short side is 3 cm and the other is 
4 cm. Plugging into the formula: 3² + 4² = 9 + 16 = 25. So c² = 25, which means c = 5 cm. 
This 3-4-5 triangle is one of the most famous in mathematics and appears everywhere from 
construction to navigation.`
            },
            {
              heading: 'Why Does It Matter?',
              body: `Pythagoras' Theorem is the foundation for calculating distances in 2D space. 
Architects use it to check if a corner is truly square. GPS systems use it (in extended 
form) to calculate your exact position. Any time you need the straight-line distance 
between two points, this theorem is at work.`
            }
          ]
        }
      },
      {
        topicId: 'trig-ratios',
        title: 'Trigonometric Ratios',
        duration: '20 min',
        lessonContent: {
          slides: [
            {
              heading: 'Sine, Cosine and Tangent',
              body: `Trigonometric ratios describe the relationship between the angles and sides of 
a right-angled triangle. For any angle θ (theta) in the triangle: sin(θ) = Opposite ÷ 
Hypotenuse, cos(θ) = Adjacent ÷ Hypotenuse, tan(θ) = Opposite ÷ Adjacent. A handy 
memory trick: SOH-CAH-TOA.`
            },
            {
              heading: 'Reading the Unit Circle',
              body: `The unit circle is a circle with radius 1 centred at the origin. As a point 
travels around it, its x-coordinate equals cos(θ) and its y-coordinate equals sin(θ) 
at every angle θ. This is why sin and cos always stay between −1 and +1, and why they 
repeat in a smooth wave pattern.`
            },
            {
              heading: 'Putting It to Use',
              body: `Suppose a ladder leans against a wall at an angle of 60° and is 5 m long. 
How high does it reach? The height is the side opposite 60°, and the ladder is the 
hypotenuse, so: height = 5 × sin(60°) ≈ 5 × 0.866 = 4.33 m. Trig ratios turn angle 
information into real measurements.`
            }
          ]
        }
      }
    ]
  },
  {
    subject: 'Science',
    subjectId: 'science',
    descriptor: 'Biology & Physics',
    topics: [
      {
        topicId: 'photosynthesis',
        title: 'Photosynthesis',
        duration: '20 min',
        lessonContent: {
          slides: [
            {
              heading: 'The Big Idea',
              body: `Photosynthesis is the process by which plants, algae, and some bacteria convert 
sunlight into food. Using light energy, they transform carbon dioxide (CO₂) from the air 
and water (H₂O) from the soil into glucose — a sugar the plant uses for energy and growth. 
Oxygen is released as a by-product, which is why plants are essential to life on Earth.`
            },
            {
              heading: 'Inside the Leaf',
              body: `Photosynthesis happens in the chloroplasts — tiny structures inside plant cells 
packed with a green pigment called chlorophyll. Chlorophyll absorbs red and blue light most 
efficiently (which is why it reflects green back to our eyes). The process has two stages: 
the light-dependent reactions capture energy from sunlight, and the Calvin cycle uses that 
energy to build glucose molecules.`
            },
            {
              heading: 'The Equation',
              body: `The overall reaction can be written as: 6CO₂ + 6H₂O + light energy → C₆H₁₂O₆ + 6O₂. 
Read it as: six molecules of carbon dioxide plus six of water, powered by light, produce one 
glucose molecule and six oxygen molecules. Every breath of fresh air you take is partly 
thanks to this reaction happening in plants around you.`
            }
          ]
        }
      },
      {
        topicId: 'em-induction',
        title: 'Electromagnetic Induction',
        duration: '20 min',
        lessonContent: {
          slides: [
            {
              heading: 'How Moving Magnets Make Electricity',
              body: `Electromagnetic induction is the production of an electric current by a changing 
magnetic field. Michael Faraday discovered in 1831 that when a magnet moves through a coil 
of wire, it pushes electrons through the wire — creating a current. The faster the magnet 
moves, or the stronger it is, the larger the current produced.`
            },
            {
              heading: "Faraday's Law",
              body: `Faraday's Law states that the induced voltage (EMF) in a coil equals the rate of 
change of magnetic flux through it. In plain terms: the quicker the magnetic field changes, 
the greater the voltage. Adding more turns to the coil multiplies the effect — each loop 
contributes its own small voltage, and they all add up.`
            },
            {
              heading: 'Where You See It Every Day',
              body: `Every electrical generator — from a power station turbine to a bicycle dynamo — 
works by spinning a coil inside a magnetic field, continuously changing the flux and 
producing alternating current. Induction charging pads in your phone use the same principle 
with a coil in the pad and a coil in the device, no wire contact needed.`
            }
          ]
        }
      }
    ]
  },
  {
    subject: 'English',
    subjectId: 'english',
    descriptor: 'Language & Literature',
    topics: [
      {
        topicId: 'plot-arc',
        title: 'Story Structure & Plot Arc',
        duration: '20 min',
        lessonContent: {
          slides: [
            {
              heading: 'The Shape of a Story',
              body: `Almost every story — from ancient myths to modern films — follows a recognisable 
shape called the plot arc (or Freytag's Pyramid). It has five stages: Exposition (the setup), 
Rising Action (complications build), Climax (the turning point of highest tension), Falling 
Action (consequences unfold), and Resolution (the new normal). Recognising this shape helps 
you both analyse stories you read and construct ones you write.`
            },
            {
              heading: 'Rising Action & the Climax',
              body: `Rising action is where the story earns its climax. The protagonist faces a series 
of obstacles or conflicts — internal (self-doubt, grief) or external (an antagonist, 
nature, society) — that escalate in stakes and difficulty. The climax is the single moment 
where the central conflict reaches its peak. Everything before it builds toward this point; 
everything after flows from it.`
            },
            {
              heading: 'Resolution and Why It Matters',
              body: `The resolution isn't just "the ending" — it shows how the world and characters 
have changed because of the story's events. A strong resolution feels earned: it answers 
the central question the story posed. It can be happy, tragic, or ambiguous, but it should 
be inevitable in hindsight. When you evaluate any story, ask: does the resolution feel 
like it grew naturally from what came before?`
            }
          ]
        }
      },
      {
        topicId: 'active-passive',
        title: 'Active & Passive Voice',
        duration: '20 min',
        lessonContent: {
          slides: [
            {
              heading: 'Active vs. Passive — The Core Difference',
              body: `In an active sentence, the subject performs the action: "The dog chased the cat." 
In a passive sentence, the subject receives the action: "The cat was chased by the dog." 
Same event, different emphasis. Active voice is direct and energetic; passive voice shifts 
focus to what happened rather than who did it. Neither is wrong — choosing between them 
is about what you want to highlight.`
            },
            {
              heading: 'How to Spot (and Build) Passive Voice',
              body: `Passive voice almost always contains a form of "to be" (is, was, were, been) 
followed by a past participle (chased, written, built). The agent — the one doing the 
action — is either absent or tagged on with "by." To convert passive to active, find the 
agent, make it the subject, and drop the "to be" helper: "The report was written by Priya" 
becomes "Priya wrote the report."`
            },
            {
              heading: 'When Each Voice Works Best',
              body: `Use active voice when you want clarity and momentum — most everyday writing, 
journalism, and storytelling benefits from it. Use passive voice when the doer is unknown 
("The window was broken"), unimportant ("Mistakes were made"), or when you deliberately 
want to de-emphasise responsibility. Scientific writing traditionally uses passive to keep 
focus on the experiment rather than the researcher: "The solution was heated to 80°C."`
            }
          ]
        }
      }
    ]
  }
];
